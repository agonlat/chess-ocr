const uploadBtn = document.getElementById("uploadBtn");
const fileInput = document.getElementById("fileInput");
const resultDiv = document.getElementById("result");
const resultContainer = document.getElementById("resultContainer");
const fileNameDisplay = document.getElementById("fileNameDisplay");
// Den Download-Button aus dem HTML holen
const downloadBtn = document.getElementById('download-btn');

const API_BASE_URL = "https://v3sik2bfnb.execute-api.us-east-1.amazonaws.com/prod";

fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
        fileNameDisplay.textContent = fileInput.files[0].name;
        fileNameDisplay.style.color = "#3b82f6";
    }
});

// Hilfsfunktion für den eigentlichen Datei-Download
function downloadBlob(content, filename, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// Hilfsfunktion zur Anzeige des Ergebnisses UND Aktivierung des Downloads
function showResult(pgn, gameId = "partie") {
    resultDiv.textContent = pgn || "No PGN data found.";
    resultDiv.style.whiteSpace = "pre-wrap"; 
    uploadBtn.disabled = false;
    uploadBtn.textContent = "Start analysis";

    if (pgn) {
        // 1. Download-Button sichtbar machen
        downloadBtn.style.display = 'block';
        
        // 2. Klick-Event für den Download binden
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
    downloadBtn.style.display = 'none'; // Download bei Fehler verstecken
}

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
    downloadBtn.style.display = 'none'; // Verstecken bei neuem Upload
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
                showResult(uploadData.pgn, uploadData.file || "partie");
            } 
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
                showResult(data.pgn, gameId); // PGN anzeigen & Download aktivieren
            } else if (data.status === "ERROR") {
                clearInterval(interval);
                showError("Analysis failed: " + (data.error || "Unknown Error"));
            }

            if (attempts >= maxAttempts) {
                clearInterval(interval);
                showError("Timeout: The AI is taking too long.");
            }

        } catch (err) {
            console.log("Polling issue, retrying...", err);
        }
    }, 2000); 
}