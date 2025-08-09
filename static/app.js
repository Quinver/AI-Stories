var modal = document.getElementById("settingsModal");
var btn = document.getElementById("settingsBtn");
var span = document.getElementsByClassName("close")[0];
var saveBtn = document.getElementById("saveSettings");

// When the user clicks on the button, open the modal
btn.onclick = function () {
  loadSettings();
  modal.style.display = "block";
};

span.onclick = function () {
  modal.style.display = "none";
};

// When the user clicks anywhere outside of the modal, close it
window.onclick = function (event) {
  if (event.target == modal) {
    modal.style.display = "none";
  }
};

// Save settings when save button is clicked
saveBtn.onclick = function () {
  saveSettings();
  modal.style.display = "none";
};

let agents = [];
let isConversationRunning = false;

// Settings management
const DEFAULT_SETTINGS = {
  ollamaUrl: "http://localhost:11434",
  ollamaModel: "mythomax:latest",
  openaiApiKey: "",
  openaiBaseUrl: "https://api.openai.com/v1",
  openaiModel: "gpt-4o-mini",
  githubToken: "",
  githubModel: "openai/gpt-4o-mini",
};

function loadSettings() {
  const settings = JSON.parse(localStorage.getItem("aiAgentSettings") || "{}");
  const finalSettings = { ...DEFAULT_SETTINGS, ...settings };

  document.getElementById("ollamaUrl").value = finalSettings.ollamaUrl;
  document.getElementById("ollamaModel").value = finalSettings.ollamaModel;
  document.getElementById("openaiApiKey").value = finalSettings.openaiApiKey;
  document.getElementById("openaiBaseUrl").value = finalSettings.openaiBaseUrl;
  document.getElementById("openaiModel").value = finalSettings.openaiModel;
  document.getElementById("githubToken").value = finalSettings.githubToken;
  document.getElementById("githubModel").value = finalSettings.githubModel;
}

function saveSettings() {
  const settings = {
    ollamaUrl: document.getElementById("ollamaUrl").value.trim(),
    ollamaModel: document.getElementById("ollamaModel").value.trim(),
    openaiApiKey: document.getElementById("openaiApiKey").value.trim(),
    openaiBaseUrl: document.getElementById("openaiBaseUrl").value.trim(),
    openaiModel: document.getElementById("openaiModel").value.trim(),
    githubToken: document.getElementById("githubToken").value.trim(),
    githubModel: document.getElementById("githubModel").value.trim(),
  };

  localStorage.setItem("aiAgentSettings", JSON.stringify(settings));
  showSuccess("Settings saved successfully!");
}

function getSettings() {
  const settings = JSON.parse(localStorage.getItem("aiAgentSettings") || "{}");
  return { ...DEFAULT_SETTINGS, ...settings };
}

function resetSettings() {
  if (
    confirm("Are you sure you want to reset all settings to default values?")
  ) {
    localStorage.removeItem("aiAgentSettings");
    loadSettings();
    showSuccess("Settings reset to defaults!");
  }
}

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

function showSuccess(message) {
  const successElement = document.getElementById("successMsg");
  if (!successElement) {
    // Create success element if it doesn't exist
    const element = document.createElement("div");
    element.id = "successMsg";
    element.className = "success";
    element.style.background = "#28a745";
    element.style.color = "white";
    element.style.padding = "15px";
    element.style.borderRadius = "8px";
    element.style.margin = "10px 0";
    element.style.display = "none";
    document.querySelector(".controls").appendChild(element);
  }

  const element = document.getElementById("successMsg");
  element.textContent = message;
  element.style.display = "block";
  setTimeout(() => {
    element.style.display = "none";
  }, 3000);
}

function showLoading(show) {
  document.getElementById("loading").style.display = show ? "block" : "none";
  document.getElementById("startChat").disabled = show;
}

function clearChat() {
  const container = document.getElementById("chatContainer");
  container.innerHTML = '<div class="status">Starting conversation...</div>';

  // Scroll to top when clearing chat
  container.scrollTo({
    top: 0,
    behavior: "smooth",
  });
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

  // Smooth scroll to the bottom
  setTimeout(() => {
    container.scrollTo({
      top: container.scrollHeight,
      behavior: "smooth",
    });
  }, 100); // Small delay to ensure the message is fully rendered
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
  const settings = getSettings();

  for (let turn = 0; turn < turns; turn++) {
    const currentAgent = selectedAgents[turn % selectedAgents.length];

    try {
      const requestBody = {
        prompt: currentPrompt,
        agent_name: currentAgent,
        api: api,
        settings: settings, // Pass settings to backend
      };

      const response = await fetch("/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
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

// Test connection functions
async function testOllamaConnection() {
  const settings = {
    ollamaUrl: document.getElementById("ollamaUrl").value.trim(),
    ollamaModel: document.getElementById("ollamaModel").value.trim(),
  };

  try {
    const response = await fetch("/test-connection", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        api: "ollama",
        settings: settings,
      }),
    });

    const data = await response.json();

    if (response.ok) {
      showSuccess(data.message);
    } else {
      showError(data.detail || "Ollama connection failed");
    }
  } catch (error) {
    showError("Ollama connection test failed: " + error.message);
  }
}

async function testOpenAIConnection() {
  const settings = {
    openaiApiKey: document.getElementById("openaiApiKey").value.trim(),
    openaiBaseUrl: document.getElementById("openaiBaseUrl").value.trim(),
    openaiModel: document.getElementById("openaiModel").value.trim(),
  };

  if (!settings.openaiApiKey) {
    showError("Please enter an OpenAI API key first");
    return;
  }

  try {
    const response = await fetch("/test-connection", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        api: "openai",
        settings: settings,
      }),
    });

    const data = await response.json();

    if (response.ok) {
      showSuccess(data.message);
    } else {
      showError(data.detail || "OpenAI connection failed");
    }
  } catch (error) {
    showError("OpenAI connection test failed: " + error.message);
  }
}

async function testGitHubConnection() {
  const settings = {
    githubToken: document.getElementById("githubToken").value.trim(),
    githubModel: document.getElementById("githubModel").value.trim(),
  };

  if (!settings.githubToken) {
    showError("Please enter a GitHub token first");
    return;
  }

  try {
    const response = await fetch("/test-connection", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        api: "github",
        settings: settings,
      }),
    });

    const data = await response.json();

    if (response.ok) {
      showSuccess(data.message);
    } else {
      showError(data.detail || "GitHub Models connection failed");
    }
  } catch (error) {
    showError("GitHub Models connection test failed: " + error.message);
  }
}

// Event listeners
document
  .getElementById("startChat")
  .addEventListener("click", startConversation);
document
  .getElementById("clearMemory")
  .addEventListener("click", clearAllMemory);
document
  .getElementById("resetSettings")
  .addEventListener("click", resetSettings);
document
  .getElementById("testOllama")
  .addEventListener("click", testOllamaConnection);
document
  .getElementById("testOpenAI")
  .addEventListener("click", testOpenAIConnection);
document
  .getElementById("testGitHub")
  .addEventListener("click", testGitHubConnection);

document.getElementById("prompt").addEventListener("keydown", function (e) {
  if (e.key === "Enter" && e.ctrlKey) {
    startConversation();
  }
});

// Load agents when page loads
loadAgents();

// Initialize settings on page load
document.addEventListener("DOMContentLoaded", function () {
  loadSettings();
});
