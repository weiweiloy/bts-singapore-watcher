// girlwithticket Worker
// - Receives Telegram webhook calls.
// - "check now" → trigger a GitHub Actions run and acknowledge.
// - Any other message → reply with the sender's chat ID.

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("girlwithticket is alive 🎟️");
    }

    const telegramSecret = request.headers.get(
      "x-telegram-bot-api-secret-token"
    );
    if (telegramSecret !== env.WEBHOOK_SECRET) {
      return new Response("Unauthorized", { status: 401 });
    }

    let update;
    try {
      update = await request.json();
    } catch {
      return new Response("Bad request", { status: 400 });
    }

    const message = update.message;
    if (!message || !message.chat || !message.chat.id) {
      return new Response("ok");
    }

    const chatId = message.chat.id;
    const firstName = message.chat.first_name || "there";
    const text = (message.text || "").trim().toLowerCase();

    if (text === "check now" || text === "/check") {
      await triggerGithubCheck(env);
      await sendTelegramMessage(
        env.BOT_TOKEN,
        chatId,
        "👍 Check kicked off. You'll get the result in about a minute."
      );
      return new Response("ok");
    }

    const reply =
      `Hi ${firstName}!\n\n` +
      `Your Telegram chat ID is:\n\n` +
      `${chatId}\n\n` +
      `Send this number to Wei so she can add you to the girlwithticket ` +
      `alert list. Once added, you'll get BTS Singapore ticket alerts here. 💜\n\n` +
      `Tip: once you're on the list, send "check now" to trigger a fresh ` +
      `check anytime.`;

    await sendTelegramMessage(env.BOT_TOKEN, chatId, reply);
    return new Response("ok");
  },
};

async function sendTelegramMessage(token, chatId, text) {
  const url = `https://api.telegram.org/bot${token}/sendMessage`;
  await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      disable_web_page_preview: true,
    }),
  });
}

async function triggerGithubCheck(env) {
  const url = `https://api.github.com/repos/${env.GITHUB_REPO}/dispatches`;
  await fetch(url, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "girlwithticket-worker",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ event_type: "manual-check" }),
  });
}
