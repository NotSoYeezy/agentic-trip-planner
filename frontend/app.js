const API_URL = "http://localhost:8000";

const form = document.getElementById("trip-form");
const submitBtn = document.getElementById("submit-btn");
const statusEl = document.getElementById("status");
const outputEl = document.getElementById("output");
const responseText = document.getElementById("response-text");

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const origin = document.getElementById("origin").value;
    const destination = document.getElementById("destination").value;
    const dateFrom = document.getElementById("date-from").value;
    const dateTo = document.getElementById("date-to").value;
    const budget = document.getElementById("budget").value;

    const message =
        `I want to fly from ${origin} to ${destination}, ` +
        `${dateFrom} - ${dateTo}, ` +
        `i have ${budget} usd budget`;

    submitBtn.disabled = true;
    submitBtn.textContent = "Planning...";
    responseText.textContent = "";
    outputEl.classList.remove("hidden");
    statusEl.classList.remove("hidden");
    statusEl.classList.remove("tool-active");
    statusEl.textContent = "Connecting...";

    try {
        const response = await fetch(`${API_URL}/plan/stream`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, thread_id: 1 }),
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        statusEl.textContent = "Generating plan...";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            const lines = buffer.split("\n");
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;

                const data = line.slice(6).trim();
                if (data === "[DONE]") {
                    statusEl.textContent = "Done!";
                    statusEl.classList.remove("tool-active");
                    continue;
                }

                try {
                    const parsed = JSON.parse(data);
                    const content = parsed.content;

                    if (content.includes("[TOOL_START:")) {
                        const toolName = content.match(/\[TOOL_START:\s*(.+?)\]/)?.[1];
                        statusEl.textContent = `Running: ${toolName}...`;
                        statusEl.classList.add("tool-active");
                    } else if (content.includes("[TOOL_END:")) {
                        statusEl.textContent = "Generating plan...";
                        statusEl.classList.remove("tool-active");
                    }

                    responseText.textContent += content;
                    outputEl.scrollTop = outputEl.scrollHeight;
                } catch {
                }
            }
        }
    } catch (err) {
        statusEl.textContent = `Error: ${err.message}`;
        statusEl.classList.remove("tool-active");
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Plan My Trip";
    }
});
