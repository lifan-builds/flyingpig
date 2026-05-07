from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Amex Mock Chat Server")

MOCK_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>American Express Mock</title>
</head>
<body>
    <h1>Welcome to American Express</h1>
    <div id="login-container">
        <input type="text" id="username" placeholder="User ID" />
        <input type="password" id="password" placeholder="Password" />
        <button id="login-btn">Log In</button>
    </div>

    <div id="chat-container" style="display:none; margin-top:20px;">
        <button id="open-chat">Chat with Us</button>
        <div
            id="chat-window"
            style="display:none; border:1px solid black; padding:10px; width:300px;"
        >
            <div id="chat-history"></div>
            <input type="text" id="chat-input" placeholder="Type here..." />
            <button id="chat-send">Send</button>
        </div>
    </div>

    <script>
        const loginBtn = document.getElementById("login-btn");
        const openChatBtn = document.getElementById("open-chat");
        const chatSendBtn = document.getElementById("chat-send");
        const chatInput = document.getElementById("chat-input");
        const chatHistory = document.getElementById("chat-history");

        // Ensure browser waits for events via standard DOM manipulation
        loginBtn.addEventListener("click", () => {
            const u = document.getElementById("username").value;
            const p = document.getElementById("password").value;
            if (u && p) {
                document.getElementById("login-container").style.display = "none";
                document.getElementById("chat-container").style.display = "block";
            }
        });

        openChatBtn.addEventListener("click", () => {
            document.getElementById("chat-window").style.display = "block";
            openChatBtn.style.display = "none";
            chatHistory.innerHTML += "<div>Agent: Hi, how can I help you today?</div>";
        });

        let msgCount = 0;
        chatSendBtn.addEventListener("click", () => {
            const val = chatInput.value;
            if (!val) return;
            chatHistory.innerHTML += "<div>You: " + val + "</div>";
            chatInput.value = "";
            msgCount++;

            setTimeout(() => {
                if (msgCount === 1) {
                    chatHistory.innerHTML += [
                        "<div>Agent: I understand you want to cancel. ",
                        "I can offer you a $50 statement credit to stay. (AI)</div>",
                    ].join("");
                } else if (msgCount === 2) {
                    chatHistory.innerHTML += [
                        "<div>Agent: The $50 statement credit has been applied. ",
                        "Your confirmation number is MOCK-12345.</div>",
                    ].join("");
                } else {
                    chatHistory.innerHTML += [
                        "<div>Agent: Is there anything else ",
                        "I can help you with?</div>",
                    ].join("");
                }
            }, 1000);
        });
    </script>
</body>
</html>
"""


@app.get("/")
async def root(logged_in: bool = False):
    html = MOCK_HTML
    if logged_in:
        html = html.replace(
            '<div id="login-container">',
            '<div id="login-container" style="display:none;">',
        ).replace(
            '<div id="chat-container" style="display:none; margin-top:20px;">',
            '<div id="chat-container" style="display:block; margin-top:20px;">',
        )
    return HTMLResponse(content=html)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8086)
