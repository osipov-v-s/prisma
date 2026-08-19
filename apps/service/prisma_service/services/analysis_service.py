"""Application orchestration for analytics requests."""

from prisma.analytics import compare_analysis_modes

from ..mappers import to_collection_schema, to_pair_responses, to_session_metadata
from ..models import CompareAnalysisRequest


def compare_analysis(request: CompareAnalysisRequest) -> dict:
    collection = to_collection_schema(request.collection)
    responses = to_pair_responses(request.responses)
    session = to_session_metadata(request.session)
    result = compare_analysis_modes(
        responses=responses,
        collection_schema=collection,
        time_algorithm=request.settings.time_algorithm,
        iteration_strategy=request.settings.iteration_strategy,
        epsilon=request.settings.epsilon,
        max_iterations=request.settings.max_iterations,
        session_metadata=session,
    )
    return result.to_dict()
