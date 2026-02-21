/**
 * Lógica del frontend NeoGuard Image Gen.
 *
 * FASE 1 - Inicialización:
 *   - loadModels() obtiene /models y /edit-info en paralelo.
 *   - populateEditModels() llena el select de modelos de edición.
 *   - updateFormatHint() muestra formatos permitidos (PNG, JPEG, etc.).
 *
 * FASE 2 - Tabs:
 *   - Al hacer clic en Generar/Editar se alterna la visibilidad de las secciones.
 *
 * FASE 3 - Formulario Generar:
 *   - Al cambiar proveedor, se actualiza el dropdown de modelos.
 *   - Al enviar: FormData con prompt + model -> POST /generation/{provider}.
 *
 * FASE 4 - Formulario Editar:
 *   - Valida cantidad de archivos (1-16) antes de enviar.
 *   - FormData con prompt, model, images[] -> POST /generation/openai/edit.
 *
 * FASE 5 - Resultado:
 *   - displayResult() muestra texto o imagen (base64 con prefijo data:image/...).
 *   - showError() muestra mensajes de error en la misma área.
 */
document.addEventListener('DOMContentLoaded', () => {
    const providerSelect = document.getElementById('provider');
    const modelSelect = document.getElementById('model');
    const form = document.getElementById('generation-form');
    const generateBtn = document.getElementById('generate-btn');
    const btnText = generateBtn.querySelector('.btn-text');
    const loader = generateBtn.querySelector('.loader-dots');
    const resultSection = document.getElementById('result-section');
    const resultContent = document.getElementById('result-content');
    const modelTag = document.getElementById('model-tag');

    const editForm = document.getElementById('edit-form');
    const editImagesInput = document.getElementById('edit-images');
    const editModelSelect = document.getElementById('edit-model');
    const editPromptInput = document.getElementById('edit-prompt');
    const editBtn = document.getElementById('edit-btn');
    const editBtnText = editBtn.querySelector('.btn-text');
    const editLoader = editBtn.querySelector('.loader-dots');
    const formatHint = document.getElementById('format-hint');
    const editFilesCount = document.getElementById('edit-files-count');

    const API_BASE_URL = '/api/v1';

    let allModelsData = [];
    let editInfo = null;

    // Cargar modelos (para dropdown de generación) y edit-info (formatos, modelos de edición)
    async function loadModels() {
        try {
            const [modelsRes, editRes] = await Promise.all([
                fetch(`${API_BASE_URL}/generation/models`),
                fetch(`${API_BASE_URL}/generation/edit-info`)
            ]);
            if (!modelsRes.ok) throw new Error('No se pudieron cargar los modelos');
            if (!editRes.ok) throw new Error('No se pudo cargar info de edición');
            allModelsData = await modelsRes.json();
            editInfo = await editRes.json();
            console.log('Modelos cargados:', allModelsData);
            populateEditModels();
            updateFormatHint();
        } catch (error) {
            console.error('Error loading:', error);
            showError('Error al conectar con la API central.');
        }
    }

    // Llena el select de modelos con los que soportan edición (gpt-image-1.5, etc.)
    function populateEditModels() {
        if (!editInfo?.models) return;
        editModelSelect.innerHTML = '<option value="" disabled selected>Selecciona modelo</option>';
        editInfo.models.forEach(id => {
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = id;
            editModelSelect.appendChild(opt);
        });
    }

    // Muestra "Formatos permitidos: PNG, JPEG, GIF, WEBP (1-16 imágenes)"
    function updateFormatHint() {
        if (!editInfo) return;
        formatHint.textContent = `Formatos permitidos: ${editInfo.allowed_formats} (${editInfo.min_images}-${editInfo.max_images} imágenes)`;
    }

    // Tabs: Generar / Editar
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const mode = btn.dataset.mode;
            document.getElementById('generate-section').style.display = mode === 'generate' ? 'block' : 'none';
            document.getElementById('edit-section').style.display = mode === 'edit' ? 'block' : 'none';
        });
    });

    editImagesInput.addEventListener('change', () => {
        const n = editImagesInput.files?.length || 0;
        editFilesCount.textContent = n > 0 ? `${n} archivo(s) seleccionado(s)` : '';
    });

    // 2. Actualizar modelos cuando cambia el proveedor
    providerSelect.addEventListener('change', () => {
        const selectedProvider = providerSelect.value;
        const providerData = allModelsData.find(p => p.provider.toLowerCase() === selectedProvider.toLowerCase());

        modelSelect.innerHTML = '<option value="" disabled selected>Selecciona un modelo</option>';
        
        if (providerData && providerData.models) {
            providerData.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = `${model.id} (${model.type})`;
                modelSelect.appendChild(option);
            });
            modelSelect.disabled = false;
        } else {
            modelSelect.disabled = true;
        }
    });

    // 3. Manejar envío del formulario
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const provider = providerSelect.value;
        const model = modelSelect.value;
        const prompt = document.getElementById('prompt').value;

        setLoading(true);
        resultSection.style.display = 'none';

        try {
            // FormData: la API usa Form() para prompt y model, no JSON
            const formData = new FormData();
            formData.append('prompt', prompt);
            formData.append('model', model);

            const convId = document.getElementById('conversation-id').value.trim();
            if (convId) {
                formData.append('conversation_id', convId);
                formData.append('use_summary_context', document.getElementById('use-summary-context').checked);
            }

            const response = await fetch(`${API_BASE_URL}/generation/${provider}`, {
                method: 'POST',
                body: formData
            });

            const text = await response.text();
            let data;
            try {
                data = JSON.parse(text);
            } catch {
                throw new Error(response.ok ? 'Error desconocido' : (text || `Error ${response.status}`));
            }

            if (!response.ok) {
                throw new Error(data.detail || 'Error en la generación');
            }

            displayResult(data, provider);
        } catch (error) {
            console.error('Error in generation:', error);
            showError(error.message);
        } finally {
            setLoading(false);
        }
    });

    // 4. Envío del formulario de edición
    editForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const prompt = editPromptInput.value.trim();
        const model = editModelSelect.value;
        const files = editImagesInput.files;

        if (!files?.length) {
            showError('Selecciona al menos una imagen.');
            return;
        }
        if (editInfo && files.length > editInfo.max_images) {
            showError(`Máximo ${editInfo.max_images} imágenes.`);
            return;
        }

        setEditLoading(true);
        resultSection.style.display = 'block';
        resultContent.innerHTML = '<p>Procesando...</p>';

        try {
            const formData = new FormData();
            formData.append('prompt', prompt);
            formData.append('model', model);
            for (let i = 0; i < files.length; i++) {
                formData.append('images', files[i]);
            }

            const response = await fetch(`${API_BASE_URL}/generation/openai/edit`, {
                method: 'POST',
                body: formData
            });

            const text = await response.text();
            let data;
            try {
                data = JSON.parse(text);
            } catch {
                throw new Error(response.ok ? 'Error desconocido' : (text || `Error ${response.status}`));
            }

            if (!response.ok) {
                throw new Error(data.detail || 'Error en la edición');
            }

            displayResult(data, 'openai');
        } catch (error) {
            console.error('Error in edit:', error);
            showError(error.message);
        } finally {
            setEditLoading(false);
        }
    });

    function setEditLoading(isLoading) {
        editBtn.disabled = isLoading;
        editBtnText.style.display = isLoading ? 'none' : 'block';
        editLoader.style.display = isLoading ? 'flex' : 'none';
    }

    function displayResult(data, provider) {
        resultSection.style.display = 'block';
        modelTag.textContent = `${data.provider} | ${data.model_used}`;
        resultContent.innerHTML = '';

        if (data.image_base64) {
            const mime = data.image_mime_type || 'image/png';
            const dataUrl = `data:${mime};base64,${data.image_base64}`;
            const img = document.createElement('img');
            img.src = dataUrl;
            img.alt = 'Imagen generada';
            resultContent.appendChild(img);
        } else if (data.content) {
            const p = document.createElement('p');
            p.textContent = data.content;
            resultContent.appendChild(p);
        }

        resultSection.scrollIntoView({ behavior: 'smooth' });
    }

    function showError(msg) {
        resultSection.style.display = 'block';
        modelTag.textContent = 'Error';
        resultContent.innerHTML = `<p style="color: #ef4444;">${msg}</p>`;
    }

    function setLoading(isLoading) {
        generateBtn.disabled = isLoading;
        btnText.style.display = isLoading ? 'none' : 'block';
        loader.style.display = isLoading ? 'flex' : 'none';
        if (isLoading) {
            resultContent.innerHTML = '<p>Procesando...</p>';
        }
    }

    loadModels();
});
