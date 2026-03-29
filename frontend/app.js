const uploadBtn = document.getElementById("uploadBtn");
const fileInput = document.getElementById("fileInput");
const resultDiv = document.getElementById("result");
const resultContainer = document.getElementById("resultContainer");
const fileNameDisplay = document.getElementById("fileNameDisplay");

// API URLs
const API_BASE_URL = "https://v3sik2bfnb.execute-api.us-east-1.amazonaws.com/prod";

fileInput.addEventListener("change", () => {
  if (fileInput.files.length > 0) {
    fileNameDisplay.textContent = fileInput.files[0].name;
    fileNameDisplay.style.color = "#3b82f6";
  }
});

uploadBtn.addEventListener("click", () => {
  const file = fileInput.files[0];
  if (!file) {
    alert("Please select a file first!");
    return;
  }

  // UI Vorbereiten
  uploadBtn.disabled = true;
  uploadBtn.textContent = "Analyzing Game...";
  resultContainer.classList.remove("hidden");
  resultDiv.style.color = "#10b981"; // Zurück auf Grün setzen falls vorher Error
  resultDiv.textContent = "Uploading image and starting AI analysis...";

  const reader = new FileReader();
  reader.onload = async () => {
    const base64 = reader.result.split(",")[1];
    
    try {
      // STEP 1: Upload & Initialer Start
      const uploadResponse = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: base64 })
      });

      const uploadData = await uploadResponse.json();

      // FALL A: Lambda war schnell und schickt PGN direkt zurück
      if (uploadData.status === "COMPLETED" || uploadData.pgn) {
        showResult(uploadData.pgn);
      } 
      // FALL B: Lambda arbeitet noch (ID vorhanden), wir müssen pollen
      else if (uploadData.file) {
        resultDiv.textContent = "Image uploaded. Deep analysis in progress (this can take up to 60s)...";
        pollForResult(uploadData.file);
      } else {
        throw new Error("No File ID or PGN received from Server.");
      }

    } catch (err) {
      console.error("Upload Error:", err);
      showError("Error communicating with the AI. Check Lambda Logs.");
    }
  };
  reader.readAsDataURL(file);
});

// Hilfsfunktion zur Anzeige des Ergebnisses
function showResult(pgn) {
  resultDiv.textContent = pgn || "No PGN data found.";
  resultDiv.style.whiteSpace = "pre-wrap"; 
  uploadBtn.disabled = false;
  uploadBtn.textContent = "Start analysis";
}

// Hilfsfunktion für Fehler
function showError(msg) {
  resultDiv.textContent = msg;
  resultDiv.style.color = "#ef4444";
  uploadBtn.disabled = false;
  uploadBtn.textContent = "Try again";
}

async function pollForResult(gameId) {
  const maxAttempts = 60; // Erhöht auf 120 Sekunden (60 * 2s)
  let attempts = 0;

  const interval = setInterval(async () => {
    attempts++;
    try {
      // API Aufruf um den Status aus DynamoDB/S3 zu prüfen
      const response = await fetch(`${API_BASE_URL}/chess-api-handler?game_id=${gameId}`);
      const data = await response.json();

      if (response.status === 200 && data.status === "COMPLETED") {
        clearInterval(interval);
        showResult(data.pgn);
      } else if (data.status === "ERROR") {
        clearInterval(interval);
        showError("Analysis failed: " + (data.error || "Unknown Error"));
      }

      // Timeout Check
      if (attempts >= maxAttempts) {
        clearInterval(interval);
        showError("Timeout: The AI is taking too long. Please try a clearer image.");
      }

    } catch (err) {
      console.log("Polling connection issue, retrying...", err);
    }
  }, 2000); 
}