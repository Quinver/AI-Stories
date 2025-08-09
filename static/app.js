var modal = document.getElementById("settingsModal");
var btn = document.getElementById("settingsBtn");
var span = document.getElementsByClassName("close")[0];

// When the user clicks on the button, open the modal
btn.onclick = function() {
  modal.style.display = "block";
}
span.onclick = function() {
  modal.style.display = "none";
}

// When the user clicks anywhere outside of the modal, close it
window.onclick = function(event) {
  if (event.target == modal) {
    modal.style.display = "none";
  }
} 

let agents = [];
let isConversationRunning = false;

async function loadAgents() {
  try {
    const response = await fetch("/agents");
    agents = await response.json();
    populateAgentSelector();
  } catch (error) {
    showError("Failed to load agents: " + error.message);
  }
}

function populateAgentSelector() {
  const selector = document.getElementById("agentSelector");
  selector.innerHTML = "";

  agents.forEach((agent) => {
    const div = document.createElement("div");
    div.className = "agent-checkbox";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.id = `agent-${agent.name}`;
    checkbox.value = agent.name;
    checkbox.checked = true; 

    const label = document.createElement("label");
    label.htmlFor = checkbox.id;
    label.textContent = agent.name;
    label.style.marginBottom = "0";
    label.style.cursor = "pointer";

    div.appendChild(checkbox);
    div.appendChild(label);
    selector.appendChild(div);
  });
}

function getSelectedAgents() {
  const checkboxes = document.querySelectorAll(
    '#agentSelector input[type="checkbox"]:checked',
  );
  return Array.from(checkboxes).map((cb) => cb.value);
}

function showError(message) {
  const errorElement = document.getElementById("errorMsg");
  errorElement.textContent = message;
  errorElement.style.display = "block";
  setTimeout(() => {
    errorElement.style.display = "none";
  }, 5000);
}

function showLoading(show) {
  document.getElementById("loading").style.display = show ? "block" : "none";
  document.getElementById("startChat").disabled = show;
}

function clearChat() {
  const container = document.getElementById("chatContainer");
  container.innerHTML = '<div class="status">Starting conversation...</div>';
}

function addMessage(speaker, content) {
  const container = document.getElementById("chatContainer");

  const status = container.querySelector(".status");
  if (status) {
    status.remove();
  }

  const messageDiv = document.createElement("div");
  messageDiv.className = `message agent-${speaker.toLowerCase().replace(/[^a-z]/g, "-")}`;

  const speakerDiv = document.createElement("div");
  speakerDiv.className = "speaker";
  speakerDiv.textContent = speaker;

  const contentDiv = document.createElement("div");
  contentDiv.className = "content";
  contentDiv.textContent = content;

  messageDiv.appendChild(speakerDiv);
  messageDiv.appendChild(contentDiv);
  container.appendChild(messageDiv);

  // Scroll to the bottom
  container.scrollTop = container.scrollHeight;
}

async function startConversation() {
  if (isConversationRunning) return;

  const selectedAgents = getSelectedAgents();
  if (selectedAgents.length < 2) {
    showError("Please select at least 2 agents for a conversation");
    return;
  }

  const prompt = document.getElementById("prompt").value.trim();
  if (!prompt) {
    showError("Please enter a conversation prompt");
    return;
  }

  const turns = parseInt(document.getElementById("turns").value);
  const api = document.getElementById("api").value;

  isConversationRunning = true;
  showLoading(true);
  clearChat();

  try {
    await startStreamingConversation(selectedAgents, prompt, turns, api);
  } catch (error) {
    showError("Failed to start conversation: " + error.message);
  } finally {
    showLoading(false);
    isConversationRunning = false;
  }
}

async function startStreamingConversation(selectedAgents, prompt, turns, api) {
  let currentPrompt = prompt;

  for (let turn = 0; turn < turns; turn++) {
    const currentAgent = selectedAgents[turn % selectedAgents.length];

    try {
      const response = await fetch("/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          prompt: currentPrompt,
          agent_name: currentAgent,
          api: api,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Chat failed");
      }

      const data = await response.json();
      const message = data.response;

      addMessage(currentAgent, message);

      // Update the prompt for the next agent to be the last response
      currentPrompt = `${currentAgent} said: ${message}\nRespond as the next character.`;

      // Small delay between messages for readability
      await new Promise((resolve) => setTimeout(resolve, 500));
    } catch (error) {
      console.error(`Error with ${currentAgent}:`, error);
      addMessage("System", `Error with ${currentAgent}: ${error.message}`);
      break;
    }
  }
}

async function clearAllMemory() {
  if (isConversationRunning) return;

  try {
    showLoading(true);
    const response = await fetch("/clear-all-memory", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Failed to clear memory");
    }

    const data = await response.json();

    const container = document.getElementById("chatContainer");
    container.innerHTML =
      '<div class="status">All agent memories have been cleared. Ready for a fresh conversation!</div>';

    addMessage("System", "All agent memories have been cleared successfully!");
  } catch (error) {
    showError("Failed to clear memory: " + error.message);
  } finally {
    showLoading(false);
  }
}

document
  .getElementById("startChat")
  .addEventListener("click", startConversation);
document
  .getElementById("clearMemory")
  .addEventListener("click", clearAllMemory);

document.getElementById("prompt").addEventListener("keydown", function (e) {
  if (e.key === "Enter" && e.ctrlKey) {
    startConversation();
  }
});

// Load agents when page loads
loadAgents();
