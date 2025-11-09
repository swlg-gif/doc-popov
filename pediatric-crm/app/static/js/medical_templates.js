// Medical Templates Management JavaScript
let currentEditingTemplateId = null;

// Инициализация модального окна шаблонов
document.addEventListener('DOMContentLoaded', function() {
    loadTemplatesList();
});

// Загрузка списка шаблонов
async function loadTemplatesList() {
    try {
        const response = await fetch('/api/medical-templates');
        const data = await response.json();
        
        displayTemplatesList(data.templates);
    } catch (error) {
        console.error('Ошибка загрузки шаблонов:', error);
        alert('Ошибка загрузки списка шаблонов');
    }
}

// Отображение списка шаблонов
function displayTemplatesList(templates) {
    const container = document.getElementById('templatesList');
    container.innerHTML = '';
    
    if (templates.length === 0) {
        container.innerHTML = '<p class="text-muted">Шаблоны не найдены. Создайте первый шаблон.</p>';
        return;
    }
    
    templates.forEach(template => {
        const templateElement = createTemplateElement(template);
        container.appendChild(templateElement);
    });
}

// Создание элемента шаблона для списка
function createTemplateElement(template) {
    const templateElement = document.getElementById('templateListItem');
    const clone = templateElement.content.cloneNode(true);
    
    const card = clone.querySelector('.template-list-item');
    const nameElement = clone.querySelector('.template-name');
    const diagnosisElement = clone.querySelector('.template-diagnosis');
    const editButton = clone.querySelector('button[onclick="editTemplate(this)"]');
    const deleteButton = clone.querySelector('button[onclick="deleteTemplate(this)"]');
    
    nameElement.textContent = template.name;
    diagnosisElement.textContent = template.diagnosis || 'Диагноз не указан';
    editButton.setAttribute('data-template-id', template.id);
    deleteButton.setAttribute('data-template-id', template.id);
    
    return clone;
}

// Создание нового шаблона
function createNewTemplate() {
    currentEditingTemplateId = null;
    document.getElementById('templateFormTitle').textContent = 'Создание нового шаблона';
    document.getElementById('templateName').value = '';
    document.getElementById('templateDiagnosis').value = '';
    document.getElementById('templatePrescriptionsList').innerHTML = '';
    
    document.getElementById('templateForm').style.display = 'block';
    document.getElementById('templatesList').style.display = 'none';
}

// Редактирование шаблона
async function editTemplate(button) {
    const templateId = button.getAttribute('data-template-id');
    
    try {
        const response = await fetch(`/api/medical-templates/${templateId}`);
        const template = await response.json();
        
        currentEditingTemplateId = templateId;
        document.getElementById('templateFormTitle').textContent = 'Редактирование шаблона';
        document.getElementById('templateName').value = template.name;
        document.getElementById('templateDiagnosis').value = template.diagnosis || '';
        
        // Загрузка назначений
        const prescriptionsList = document.getElementById('templatePrescriptionsList');
        prescriptionsList.innerHTML = '';
        
        if (template.prescriptions && template.prescriptions.length > 0) {
            template.prescriptions.forEach(prescription => {
                addTemplatePrescription(prescription);
            });
        }
        
        document.getElementById('templateForm').style.display = 'block';
        document.getElementById('templatesList').style.display = 'none';
        
    } catch (error) {
        console.error('Ошибка загрузки шаблона:', error);
        alert('Ошибка загрузки шаблона для редактирования');
    }
}

// Сохранение шаблона
async function saveTemplate() {
    const name = document.getElementById('templateName').value.trim();
    const diagnosis = document.getElementById('templateDiagnosis').value.trim();
    
    if (!name) {
        alert('Пожалуйста, укажите название шаблона');
        return;
    }
    
    const prescriptions = Array.from(document.querySelectorAll('#templatePrescriptionsList input'))
        .map(input => input.value.trim())
        .filter(value => value !== '');
    
    const templateData = {
        name: name,
        diagnosis: diagnosis,
        prescriptions: prescriptions
    };
    
    try {
        const url = currentEditingTemplateId ? 
            `/api/medical-templates/${currentEditingTemplateId}` : 
            '/api/medical-templates';
        
        const method = currentEditingTemplateId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(templateData)
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            alert('Шаблон успешно сохранен!');
            cancelTemplateEdit();
            loadTemplatesList();
        } else {
            throw new Error(result.message || 'Ошибка сохранения');
        }
    } catch (error) {
        console.error('Ошибка сохранения шаблона:', error);
        alert('Ошибка сохранения шаблона: ' + error.message);
    }
}

// Отмена редактирования шаблона
function cancelTemplateEdit() {
    document.getElementById('templateForm').style.display = 'none';
    document.getElementById('templatesList').style.display = 'block';
    currentEditingTemplateId = null;
}

// Удаление шаблона
async function deleteTemplate(button) {
    const templateId = button.getAttribute('data-template-id');
    
    if (!confirm('Вы уверены, что хотите удалить этот шаблон?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/medical-templates/${templateId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            alert('Шаблон успешно удален!');
            loadTemplatesList();
        } else {
            throw new Error(result.message || 'Ошибка удаления');
        }
    } catch (error) {
        console.error('Ошибка удаления шаблона:', error);
        alert('Ошибка удаления шаблона: ' + error.message);
    }
}

// Добавление назначения в форму шаблона
function addTemplatePrescription(value = '') {
    const template = document.getElementById('templatePrescriptionFormItem');
    const clone = template.content.cloneNode(true);
    const input = clone.querySelector('input');
    input.value = value;
    
    document.getElementById('templatePrescriptionsList').appendChild(clone);
}

// Удаление назначения из формы шаблона
function removeTemplatePrescription(button) {
    button.closest('.template-prescription-form-item').remove();
}