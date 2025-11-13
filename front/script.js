const AUDIO_SERVICE_URL = 'http://localhost:8000';
const RAG_SERVICE_URL = 'http://localhost:8002';

const tabBtns = document.querySelectorAll('.tab-btn');
const tabContents = document.querySelectorAll('.tab-content');

tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const targetTab = btn.getAttribute('data-tab');
        
        tabBtns.forEach(b => b.classList.remove('active'));
        tabContents.forEach(c => c.classList.remove('active'));
        
        btn.classList.add('active');
        document.getElementById(`${targetTab}-tab`).classList.add('active');
        
        if (targetTab === 'document') {
            loadStats();
        }
    });
});

// ==================== SEÇÃO DE ÁUDIO ====================
// Seletores de modo
const uploadModeBtn = document.getElementById('uploadModeBtn');
const microphoneModeBtn = document.getElementById('microphoneModeBtn');
const uploadMode = document.getElementById('uploadMode');
const microphoneMode = document.getElementById('microphoneMode');

// Elementos de upload
const audioUploadArea = document.getElementById('audioUploadArea');
const audioFileInput = document.getElementById('audioFileInput');
const audioFileInfo = document.getElementById('audioFileInfo');
const audioFileName = document.getElementById('audioFileName');
const processAudioBtn = document.getElementById('processAudioBtn');

// Elementos de gravação
const startRecordBtn = document.getElementById('startRecordBtn');
const stopRecordBtn = document.getElementById('stopRecordBtn');
const micIcon = document.getElementById('micIcon');
const micStatus = document.getElementById('micStatus');
const recordingTimer = document.getElementById('recordingTimer');
const audioVisualizer = document.getElementById('audioVisualizer');
const audioPreview = document.getElementById('audioPreview');
const audioPlayback = document.getElementById('audioPlayback');
const processRecordedBtn = document.getElementById('processRecordedBtn');

// Elementos comuns
const audioLoading = document.getElementById('audioLoading');
const audioResult = document.getElementById('audioResult');
const transcription = document.getElementById('transcription');
const answer = document.getElementById('answer');

let selectedAudioFile = null;
let mediaRecorder = null;
let audioChunks = [];
let recordedBlob = null;
let recordingInterval = null;
let recordingStartTime = 0;

// ==================== ALTERNÂNCIA DE MODO ====================
uploadModeBtn.addEventListener('click', () => {
    uploadModeBtn.classList.add('active');
    microphoneModeBtn.classList.remove('active');
    uploadMode.style.display = 'block';
    microphoneMode.style.display = 'none';
    audioResult.style.display = 'none';
});

microphoneModeBtn.addEventListener('click', () => {
    microphoneModeBtn.classList.add('active');
    uploadModeBtn.classList.remove('active');
    microphoneMode.style.display = 'block';
    uploadMode.style.display = 'none';
    audioResult.style.display = 'none';
});

// ==================== MODO UPLOAD ====================
audioUploadArea.addEventListener('click', () => audioFileInput.click());

audioUploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    audioUploadArea.classList.add('dragover');
});

audioUploadArea.addEventListener('dragleave', () => {
    audioUploadArea.classList.remove('dragover');
});

audioUploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    audioUploadArea.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleAudioFileSelect(files[0]);
    }
});

audioFileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleAudioFileSelect(e.target.files[0]);
    }
});

function handleAudioFileSelect(file) {
    selectedAudioFile = file;
    audioFileName.textContent = file.name;
    audioFileInfo.style.display = 'block';
    processAudioBtn.disabled = false;
}

processAudioBtn.addEventListener('click', async () => {
    if (!selectedAudioFile) return;

    processAudioBtn.disabled = true;
    audioLoading.style.display = 'block';
    audioResult.style.display = 'none';

    const formData = new FormData();
    formData.append('file', selectedAudioFile);

    try {
        const response = await fetch(`${AUDIO_SERVICE_URL}/process-audio`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            transcription.textContent = data.transcription;
            answer.textContent = data.answer;
            audioResult.style.display = 'block';
        } else {
            showAudioError(data.detail || 'Erro ao processar áudio');
        }
    } catch (error) {
        showAudioError('Erro de conexão com o serviço de áudio: ' + error.message);
    } finally {
        audioLoading.style.display = 'none';
        processAudioBtn.disabled = false;
    }
});

function showAudioError(message) {
    audioResult.style.display = 'block';
    audioResult.innerHTML = `
        <div class="result-section error">
            <div class="result-title">Erro:</div>
            <div class="result-content">${message}</div>
        </div>
    `;
}

// ==================== MODO MICROFONE ====================
startRecordBtn.addEventListener('click', async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        audioChunks = [];
        mediaRecorder = new MediaRecorder(stream);
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = () => {
            recordedBlob = new Blob(audioChunks, { type: 'audio/webm' });
            const audioUrl = URL.createObjectURL(recordedBlob);
            audioPlayback.src = audioUrl;
            audioPreview.style.display = 'block';
            
            // Para o stream do microfone
            stream.getTracks().forEach(track => track.stop());
            
            micIcon.textContent = '✅';
            micStatus.textContent = 'Gravação concluída!';
            audioVisualizer.style.display = 'none';
        };
        
        mediaRecorder.start();
        
        // UI durante gravação
        startRecordBtn.disabled = true;
        stopRecordBtn.disabled = false;
        micIcon.textContent = '🔴';
        micStatus.textContent = 'Gravando...';
        audioVisualizer.style.display = 'flex';
        audioPreview.style.display = 'none';
        
        // Timer de gravação
        recordingStartTime = Date.now();
        recordingInterval = setInterval(updateRecordingTimer, 1000);
        
        // Animação do visualizador
        animateVisualizer();
        
    } catch (error) {
        console.error('Erro ao acessar microfone:', error);
        showAudioError('Não foi possível acessar o microfone. Verifique as permissões do navegador.');
    }
});

stopRecordBtn.addEventListener('click', () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        startRecordBtn.disabled = false;
        stopRecordBtn.disabled = true;
        
        clearInterval(recordingInterval);
    }
});

function updateRecordingTimer() {
    const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
    const seconds = (elapsed % 60).toString().padStart(2, '0');
    recordingTimer.textContent = `${minutes}:${seconds}`;
}

function animateVisualizer() {
    const bars = audioVisualizer.querySelectorAll('.visualizer-bar');
    bars.forEach((bar) => {
        const height = Math.random() * 100 + 20;
        bar.style.height = `${height}%`;
    });
    
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        setTimeout(animateVisualizer, 100);
    }
}

processRecordedBtn.addEventListener('click', async () => {
    if (!recordedBlob) return;

    processRecordedBtn.disabled = true;
    audioLoading.style.display = 'block';
    audioResult.style.display = 'none';

    const formData = new FormData();
    // Converte webm para um nome de arquivo apropriado
    formData.append('file', recordedBlob, 'recording.webm');

    try {
        const response = await fetch(`${AUDIO_SERVICE_URL}/process-audio`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            transcription.textContent = data.transcription;
            answer.textContent = data.answer;
            audioResult.style.display = 'block';
        } else {
            showAudioError(data.detail || 'Erro ao processar áudio');
        }
    } catch (error) {
        showAudioError('Erro de conexão com o serviço de áudio: ' + error.message);
    } finally {
        audioLoading.style.display = 'none';
        processRecordedBtn.disabled = false;
    }
});

// ==================== SEÇÃO DE DOCUMENTOS ====================
const pdfUploadArea = document.getElementById('pdfUploadArea');
const pdfFileInput = document.getElementById('pdfFileInput');
const pdfFileInfo = document.getElementById('pdfFileInfo');
const pdfFileName = document.getElementById('pdfFileName');
const uploadPdfBtn = document.getElementById('uploadPdfBtn');
const pdfLoading = document.getElementById('pdfLoading');
const pdfResult = document.getElementById('pdfResult');
const refreshStatsBtn = document.getElementById('refreshStatsBtn');

let selectedPdfFile = null;

pdfUploadArea.addEventListener('click', () => pdfFileInput.click());

pdfUploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    pdfUploadArea.classList.add('dragover');
});

pdfUploadArea.addEventListener('dragleave', () => {
    pdfUploadArea.classList.remove('dragover');
});

pdfUploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    pdfUploadArea.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handlePdfFileSelect(files[0]);
    }
});

pdfFileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handlePdfFileSelect(e.target.files[0]);
    }
});

function handlePdfFileSelect(file) {
    if (!file.name.endsWith('.pdf')) {
        showPdfError('Por favor, selecione apenas arquivos PDF');
        return;
    }
    
    selectedPdfFile = file;
    pdfFileName.textContent = file.name;
    pdfFileInfo.style.display = 'block';
    uploadPdfBtn.disabled = false;
}

uploadPdfBtn.addEventListener('click', async () => {
    if (!selectedPdfFile) return;

    uploadPdfBtn.disabled = true;
    pdfLoading.style.display = 'block';
    pdfResult.style.display = 'none';

    const formData = new FormData();
    formData.append('file', selectedPdfFile);

    try {
        const response = await fetch(`${RAG_SERVICE_URL}/upload-pdf`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showPdfSuccess(data);
            loadStats(); // Atualiza estatísticas
            
            selectedPdfFile = null;
            pdfFileInfo.style.display = 'none';
            pdfFileInput.value = '';
        } else {
            showPdfError(data.detail || 'Erro ao processar PDF');
        }
    } catch (error) {
        showPdfError('Erro de conexão com o serviço RAG: ' + error.message);
    } finally {
        pdfLoading.style.display = 'none';
        uploadPdfBtn.disabled = false;
    }
});

function showPdfSuccess(data) {
    pdfResult.style.display = 'block';
    pdfResult.innerHTML = `
        <div class="result-section success">
            <div class="result-title">Sucesso!</div>
            <div class="result-content">
                <strong>Arquivo:</strong> ${data.filename}<br>
                <strong>Páginas:</strong> ${data.total_pages}<br>
                <strong>Fragmentos adicionados:</strong> ${data.chunks_added}<br>
                <br>
                ${data.message}
            </div>
        </div>
    `;
}

function showPdfError(message) {
    pdfResult.style.display = 'block';
    pdfResult.innerHTML = `
        <div class="result-section error">
            <div class="result-title">Erro:</div>
            <div class="result-content">${message}</div>
        </div>
    `;
}

// ==================== ESTATÍSTICAS ====================
async function loadStats() {
    try {
        const response = await fetch(`${RAG_SERVICE_URL}/stats`);
        const data = await response.json();

        document.getElementById('totalDocs').textContent = data.total_documents;
        document.getElementById('embeddingDim').textContent = data.embedding_dimension;
        document.getElementById('modelName').textContent = data.model;
    } catch (error) {
        console.error('Erro ao carregar estatísticas:', error);
        document.getElementById('totalDocs').textContent = 'Erro';
        document.getElementById('embeddingDim').textContent = 'Erro';
        document.getElementById('modelName').textContent = 'Erro';
    }
}

refreshStatsBtn.addEventListener('click', loadStats);

loadStats();