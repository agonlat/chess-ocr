const uploadBtn = document.getElementById("uploadBtn");
const fileInput = document.getElementById("fileInput");
const resultDiv = document.getElementById("result");
const resultContainer = document.getElementById("resultContainer");
const fileNameDisplay = document.getElementById("fileNameDisplay");

// Zeige Dateinamen an, wenn ausgewählt
fileInput.addEventListener("change", () => {
  if (fileInput.files.length > 0) {
    fileNameDisplay.textContent = fileInput.files[0].name;
    fileNameDisplay.style.color = "#3b82f6";
  }
});

uploadBtn.addEventListener("click", () => {
  const file = fileInput.files[0];
  if (!file) {
    alert("Bitte zuerst eine Datei auswählen!");
    return;
  }

  uploadBtn.disabled = true;
  uploadBtn.textContent = "Analysiere Partie...";
  resultContainer.classList.remove("hidden");
  resultDiv.textContent = "Warte auf Server...";

  const reader = new FileReader();
  reader.onload = async () => {
    const base64 = reader.result.split(",")[1];
    const body = JSON.stringify({ image: base64 });

    try {
      const response = await fetch("https://v3sik2bfnb.execute-api.us-east-1.amazonaws.com/prod/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body
      });

      const data = await response.json();
      resultDiv.textContent = data.message || "Upload erfolgreich!";
    } catch (err) {
      console.error(err);
      resultDiv.textContent = "Fehler bei der Kommunikation mit der KI.";
      resultDiv.style.color = "#ef4444";
    } finally {
      uploadBtn.disabled = false;
      uploadBtn.textContent = "Analyse starten";
    }
  };

  reader.readAsDataURL(file);
});