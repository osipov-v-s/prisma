/** Automated renderer check for repeated stimulus-pair transitions. */

import type { BrowserWindow } from "electron";


export async function verifyRunnerFlow(window: BrowserWindow): Promise<void> {
  await waitFor(window, "document.querySelector('form button:not(:disabled)')");
  await window.webContents.executeJavaScript(`
    (() => {
      const setValue = (input, value) => {
        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
        setter.call(input, value);
        input.dispatchEvent(new Event('input', { bubbles: true }));
      };
      const inputs = document.querySelectorAll('form input');
      setValue(inputs[0], 'user');
      setValue(inputs[1], 'user1234');
      document.querySelector('form').requestSubmit();
    })()
  `);
  await waitFor(window, "document.querySelector('.test-card .primary-action')");
  await window.webContents.executeJavaScript(
    "document.querySelector('.test-card .primary-action').click()",
  );

  for (let choice = 0; choice < 4; choice += 1) {
    await waitFor(window, "document.querySelectorAll('.stimulus-pair button:not(:disabled)').length === 2");
    const previous = await window.webContents.executeJavaScript(
      "document.querySelector('.runner-progress span').textContent",
    ) as string;
    await window.webContents.executeJavaScript(
      "document.querySelector('.stimulus-pair button:not(:disabled)').click()",
    );
    await waitFor(
      window,
      `document.querySelector('.runner-progress span')?.textContent !== ${JSON.stringify(previous)}`,
    );
  }
}


async function waitFor(window: BrowserWindow, expression: string): Promise<void> {
  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    const found = await window.webContents.executeJavaScript(`Boolean(${expression})`);
    if (found) return;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`Renderer condition timed out: ${expression}`);
}
