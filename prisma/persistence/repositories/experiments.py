"""Queries for test sessions and their complete reproducibility trace."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Account, AnalysisResult, TestSession


class ExperimentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, session_id: str) -> TestSession | None:
        return self.session.scalar(
            select(TestSession).where(TestSession.id == session_id).options(
                selectinload(TestSession.account).selectinload(Account.profile),
                selectinload(TestSession.comparisons),
                selectinload(TestSession.analysis_results),
            )
        )

    def list_for_account(self, account_id: str) -> list[TestSession]:
        statement = (
            select(TestSession).where(TestSession.account_id == account_id)
            .options(selectinload(TestSession.comparisons), selectinload(TestSession.analysis_results))
            .order_by(TestSession.started_at.desc())
        )
        return list(self.session.scalars(statement).all())

    def list_all(self) -> list[TestSession]:
        statement = select(TestSession).options(
            selectinload(TestSession.account).selectinload(Account.profile),
            selectinload(TestSession.comparisons),
            selectinload(TestSession.analysis_results),
        ).order_by(TestSession.started_at.desc())
        return list(self.session.scalars(statement).all())

    def add(self, test_session: TestSession) -> None:
        self.session.add(test_session)

    def replace_analysis(self, test_session: TestSession, payload: dict) -> AnalysisResult:
        result = next(
            (item for item in test_session.analysis_results if item.analysis_mode == "combined"),
            None,
        )
        if result is None:
            result = AnalysisResult(analysis_mode="combined",
                                    algorithm_version=payload["algorithm_version"],
                                    result_json=payload)
            test_session.analysis_results.append(result)
        else:
            result.algorithm_version = payload["algorithm_version"]
            result.result_json = payload
        return result
