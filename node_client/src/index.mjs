const API_BASE_URL = process.env.SHOWCASE_API_URL || "http://127.0.0.1:8001";
const API_TOKEN = process.env.SHOWCASE_API_TOKEN || "";

function headers() {
  const base = { "Content-Type": "application/json" };
  if (API_TOKEN) {
    base["x-api-token"] = API_TOKEN;
  }
  return base;
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: headers(),
  });

  const text = await response.text();
  let body;
  try {
    body = text ? JSON.parse(text) : {};
  } catch {
    body = { raw: text };
  }

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${JSON.stringify(body)}`);
  }
  return body;
}

async function runChat(message) {
  const payload = await api("/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
  console.log("Chat response:\n", payload);
}

async function createReminder(message, minutes = 15) {
  const payload = await api("/reminders", {
    method: "POST",
    body: JSON.stringify({ message, minutes: Number(minutes) }),
  });
  console.log("Reminder created:\n", payload);
}

async function health() {
  const payload = await api("/health", { method: "GET" });
  console.log("Health:\n", payload);
}

async function main() {
  const [command = "health", ...rest] = process.argv.slice(2);

  switch (command) {
    case "chat": {
      const message = rest.join(" ") || "Add a task: follow up with recruiter";
      await runChat(message);
      break;
    }
    case "reminder": {
      const message = rest[0] || "Review AI portfolio";
      const minutes = rest[1] || "15";
      await createReminder(message, minutes);
      break;
    }
    case "health":
    default:
      await health();
  }
}

main().catch((error) => {
  console.error("Node client error:", error.message);
  process.exitCode = 1;
});
