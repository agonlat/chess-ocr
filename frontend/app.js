const uploadBtn = document.getElementById("uploadBtn");
const fileInput = document.getElementById("fileInput");
const resultDiv = document.getElementById("result");
const resultContainer = document.getElementById("resultContainer");
const fileNameDisplay = document.getElementById("fileNameDisplay");
const downloadBtn = document.getElementById('download-btn'); // Sicherstellen, dass die ID im HTML existiert!

const API_BASE_URL = "https://v3sik2bfnb.execute-api.us-east-1.amazonaws.com/prod";

fileInput.addEventListener("change", () => {
  if (fileInput.files.length > 0) {
    fileNameDisplay.textContent = fileInput.files[0].name;
    fileNameDisplay.style.color = "#3b82f6";
  }
});

// 1. Hilfsfunktion für den eigentlichen Download
function downloadBlob(content, filename, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// 2. Hilfsfunktion zur Anzeige UND Download-Vorbereitung
function showResult(pgn, gameId = "partie") {
    resultDiv.textContent = pgn || "No PGN data found.";
    resultDiv.style.whiteSpace = "pre-wrap"; 
    uploadBtn.disabled = false;
    uploadBtn.textContent = "Start analysis";

    if (pgn && downloadBtn) {
        downloadBtn.style.display = 'block';
        downloadBtn.onclick = function() {
            const fileName = gameId.replace(".jpg", "").replace(".png", "") + ".pgn";
            downloadBlob(pgn, fileName, 'text/plain');
        };
    }
}

function showError(msg) {
    resultDiv.textContent = msg;
    resultDiv.style.color = "#ef4444";
    uploadBtn.disabled = false;
    uploadBtn.textContent = "Try again";
    if(downloadBtn) downloadBtn.style.display = 'none';
}

// 3. Upload Event
uploadBtn.addEventListener("click", () => {
  const file = fileInput.files[0];
  if (!file) {
    alert("Please select a file first!");
    return;
  }

  uploadBtn.disabled = true;
  uploadBtn.textContent = "Analyzing Game...";
  resultContainer.classList.remove("hidden");
  if(downloadBtn) downloadBtn.style.display = 'none';
  resultDiv.style.color = "#10b981"; 
  resultDiv.textContent = "Uploading image and starting AI analysis...";

  const reader = new FileReader();
  reader.onload = async () => {
    const base64 = reader.result.split(",")[1];
    
    try {
      const uploadResponse = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: base64 })
      });

      const uploadData = await uploadResponse.json();

      if (uploadData.status === "COMPLETED" || uploadData.pgn) {
        showResult(uploadData.pgn, uploadData.file);
      } 
      else if (uploadData.file) {
        resultDiv.textContent = "Image uploaded. Deep analysis in progress...";
        pollForResult(uploadData.file);
      } else {
        throw new Error("No File ID or PGN received.");
      }

    } catch (err) {
      console.error("Upload Error:", err);
      showError("Error communicating with the AI.");
    }
  };
  reader.readAsDataURL(file);
});

// 4. Polling Funktion
async function pollForResult(gameId) {
  const maxAttempts = 60; 
  let attempts = 0;

  const interval = setInterval(async () => {
    attempts++;
    try {
      const response = await fetch(`${API_BASE_URL}/chess-api-handler?game_id=${gameId}`);
      const data = await response.json();

      if (response.status === 200 && data.status === "COMPLETED") {
        clearInterval(interval);
        showResult(data.pgn, gameId);
      } else if (data.status === "ERROR") {
        clearInterval(interval);
        showError("Analysis failed: " + (data.error || "Unknown Error"));
      }

      if (attempts >= maxAttempts) {
        clearInterval(interval);
        showError("Timeout: The AI is taking too long.");
      }
    } catch (err) {
      console.log("Polling connection issue...", err);
    }
  }, 2000); 
}