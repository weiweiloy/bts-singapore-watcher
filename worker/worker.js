// girlwithticket Worker
// Receives Telegram webhook calls. When someone messages the bot,
// replies to them with their own chat ID so they can share it.

export default {
  async fetch(request, env) {
    // Healthcheck for browsers
    if (request.method !== "POST") {
      return new Response("girlwithticket is alive 🎟️");
    }

    // Verify the request is actually from Telegram by checking the
    // secret token Telegram sends in a header. We set this token when
    // we register the webhook in step 7 below.
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
      // No message to handle (could be an edit, a callback, etc.).
      // Acknowledge so Telegram doesn't retry.
      return new Response("ok");
    }

    const chatId = message.chat.id;
    const firstName = message.chat.first_name || "there";

    const reply =
      `Hi ${firstName}!\n\n` +
      `Your Telegram chat ID is:\n\n` +
      `${chatId}\n\n` +
      `Send this number to Wei so she can add ` +
      `you to the girlwithticket alert list. Once added, you'll get ` +
      `BTS Singapore ticket alerts here. 💜`;

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
