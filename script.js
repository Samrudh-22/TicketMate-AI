
function searchEvents() {
    let input = document.getElementById("searchInput")
        .value.toLowerCase();

    let cards = document.querySelectorAll(".event-card");
    let found = false;

    cards.forEach(function(card) {
        let name = card.querySelector("h3")
            .innerText.toLowerCase();

        if (name.includes(input)) {
            card.style.display = "block";
            found = true;
        } else {
            card.style.display = "none";
        }
    });

    if (!found) {
        alert("No matching events found!");
    }
}

function bookTicket(eventName) {
    window.location.href = "/book/" +
        encodeURIComponent(eventName);
}

function addChatMessage(message, sender, url) {

    const chatBox = document.getElementById("chatBox");

    const messageDiv = document.createElement("div");
    messageDiv.className = sender + "-message";
    messageDiv.textContent = message;

    chatBox.appendChild(messageDiv);

    if (url) {
        const link = document.createElement("a");
        link.href = url;
        link.textContent = "Book Your Ticket";
        link.className = "chat-book-link";

        chatBox.appendChild(link);
    }

    chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendChatMessage() {

    const input = document.getElementById("chatInput");
    const message = input.value.trim();

    if (!message) return;

    addChatMessage(message, "user");
    input.value = "";

    try {

        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message
            })
        });

        const data = await response.json();

        addChatMessage(
            data.reply,
            "bot",
            data.booking_url
        );

    } catch (error) {

        addChatMessage(
            "Sorry, something went wrong. Please try again.",
            "bot"
        );

    }
}
