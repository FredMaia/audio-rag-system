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
const audioUploadArea = document.getElementById('audioUploadArea');
const audioFileInput = document.getElementById('audioFileInput');
const audioFileInfo = document.getElementById('audioFileInfo');
const audioFileName = document.getElementById('audioFileName');
const processAudioBtn = document.getElementById('processAudioBtn');
const audioLoading = document.getElementById('audioLoading');
const audioResult = document.getElementById('audioResult');
const transcription = document.getElementById('transcription');
const answer = document.getElementById('answer');

let selectedAudioFile = null;

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