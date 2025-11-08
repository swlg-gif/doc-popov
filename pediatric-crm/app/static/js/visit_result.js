// Visit Result Form JavaScript
let currentTemplateId = null;
let formData = {
    complaints: '',
    examination: {},
    diagnosis: {},
    prescriptions: [],
    recommendations: '',
    nextVisit: null,
    payment: {}
};

// Инициализация формы
document.addEventListener('DOMContentLoaded', function() {
    initializeForm();
    setupEventListeners();
    loadDefaultTemplates();
});

function initializeForm() {
    // Установка минимальной даты для следующего визита (завтра)
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    document.getElementById('nextVisitDate').min = tomorrow.toISOString().split('T')[0];
    
    // Загрузка данных пациента, если есть
    const appointmentId = document.getElementById('appointmentId').value;
    if (appointmentId) {
        loadAppointmentData(appointmentId);
    }
}

function setupEventListeners() {
    // Обработчики для чекбоксов
    document.getElementById('scheduleNextVisit').addEventListener('change', function() {
        document.getElementById('nextVisitDetails').style.display = this.checked ? 'block' : 'none';
    });
    
    document.getElementById('dietPrescription').addEventListener('change', function() {
        document.getElementById('dietDetails').style.display = this.checked ? 'block' : 'none';
    });
    
    // Автоматический расчет суммы оплаты на основе типа приема
    document.getElementById('paymentAmount').addEventListener('change', updatePaymentSummary);
    document.getElementById('paymentStatus').addEventListener('change', updatePaymentSummary);
    document.getElementById('paymentMethod').addEventListener('change', updatePaymentSummary);
    
    // Сохранение данных формы при изменении
    setupFormAutoSave();
}

function setupFormAutoSave() {
    const inputs = document.querySelectorAll('input, textarea, select');
    inputs.forEach(input => {
        input.addEventListener('change', function() {
            saveFormData();
        });
    });
}

function saveFormData() {
    // Сохранение данных формы в объект formData
    formData.complaints = document.getElementById('complaints').value;
    formData.examination = getExaminationData();
    formData.diagnosis = getDiagnosisData();
    formData.prescriptions = getPrescriptionsData();
    formData.recommendations = document.getElementById('recommendations').value;
    formData.payment = getPaymentData();
    
    // Сохранение в localStorage
    localStorage.setItem('visitFormData', JSON.stringify(formData));
}

function loadFormData() {
    const saved = localStorage.getItem('visitFormData');
    if (saved) {
        formData = JSON.parse(saved);
        // Восстановление данных формы
        document.getElementById('complaints').value = formData.complaints || '';
        setExaminationData(formData.examination);
        setDiagnosisData(formData.diagnosis);
        setPrescriptionsData(formData.prescriptions);
        document.getElementById('recommendations').value = formData.recommendations || '';
        setPaymentData(formData.payment);
    }
}

function getExaminationData() {
    return {
        temperature: document.getElementById('temperature').value,
        weight: document.getElementById('weight').value,
        height: document.getElementById('height').value,
        condition: document.getElementById('condition').value,
        skin: document.getElementById('skin').value,
        breathing: document.getElementById('breathing').value,
        wheezing: document.getElementById('wheezing').value,
        heart: document.getElementById('heart').value,
        abdomen: document.getElementById('abdomen').value,
        throat: document.getElementById('throat').value,
        notes: document.getElementById('examinationNotes').value
    };
}

function setExaminationData(data) {
    if (!data) return;
    document.getElementById('temperature').value = data.temperature || '';
    document.getElementById('weight').value = data.weight || '';
    document.getElementById('height').value = data.height || '';
    document.getElementById('condition').value = data.condition || '';
    document.getElementById('skin').value = data.skin || '';
    document.getElementById('breathing').value = data.breathing || '';
    document.getElementById('wheezing').value = data.wheezing || '';
    document.getElementById('heart').value = data.heart || '';
    document.getElementById('abdomen').value = data.abdomen || '';
    document.getElementById('throat').value = data.throat || '';
    document.getElementById('examinationNotes').value = data.notes || '';
}

function getDiagnosisData() {
    const mainDiagnosis = document.getElementById('mainDiagnosis').value;
    const mainDiagnosisText = document.getElementById('mainDiagnosisText').value;
    const additionalDiagnoses = Array.from(document.querySelectorAll('.additional-diagnosis-item input'))
        .map(input => input.value)
        .filter(value => value.trim() !== '');
    
    const severity = document.querySelector('input[name="severity"]:checked')?.value || '';
    
    return {
        main: mainDiagnosis,
        mainText: mainDiagnosisText,
        additional: additionalDiagnoses,
        severity: severity
    };
}

function setDiagnosisData(data) {
    if (!data) return;
    document.getElementById('mainDiagnosis').value = data.main || '';
    document.getElementById('mainDiagnosisText').value = data.mainText || '';
    
    // Восстановление дополнительных диагнозов
    const container = document.getElementById('additionalDiagnosesContainer');
    container.innerHTML = '';
    if (data.additional && data.additional.length > 0) {
        data.additional.forEach(diagnosis => {
            addAdditionalDiagnosis(diagnosis);
        });
    }
    
    // Восстановление степени тяжести
    if (data.severity) {
        document.querySelector(`input[name="severity"][value="${data.severity}"]`).checked = true;
    }
}

function getPrescriptionsData() {
    const templatePrescriptions = Array.from(document.querySelectorAll('#templatePrescriptions input:checked'))
        .map(checkbox => checkbox.nextElementSibling.textContent);
    
    const manualPrescriptions = Array.from(document.querySelectorAll('.manual-prescription-item'))
        .map(item => {
            const inputs = item.querySelectorAll('input');
            return {
                medication: inputs[0].value,
                dosage: inputs[1].value,
                schedule: inputs[2].value
            };
        })
        .filter(p => p.medication.trim() !== '');
    
    const duration = document.getElementById('prescriptionDuration').value;
    const diet = document.getElementById('dietPrescription').checked ? document.getElementById('dietType').value : null;
    
    return {
        template: templatePrescriptions,
        manual: manualPrescriptions,
        duration: duration,
        diet: diet
    };
}

function setPrescriptionsData(data) {
    if (!data) return;
    
    // Восстановление ручных назначений
    const container = document.getElementById('manualPrescriptionsContainer');
    container.innerHTML = '';
    if (data.manual && data.manual.length > 0) {
        data.manual.forEach(prescription => {
            addManualPrescription(prescription.medication, prescription.dosage, prescription.schedule);
        });
    }
    
    document.getElementById('prescriptionDuration').value = data.duration || '';
    
    if (data.diet) {
        document.getElementById('dietPrescription').checked = true;
        document.getElementById('dietDetails').style.display = 'block';
        document.getElementById('dietType').value = data.diet;
    }
}

function getPaymentData() {
    return {
        amount: document.getElementById('paymentAmount').value,
        status: document.getElementById('paymentStatus').value,
        method: document.getElementById('paymentMethod').value,
        notes: document.getElementById('paymentNotes').value,
        sendReceipt: document.getElementById('sendReceipt').checked,
        createInvoice: document.getElementById('createInvoice').checked
    };
}

function setPaymentData(data) {
    if (!data) return;
    document.getElementById('paymentAmount').value = data.amount || 0;
    document.getElementById('paymentStatus').value = data.status || 'pending';
    document.getElementById('paymentMethod').value = data.method || 'cash';
    document.getElementById('paymentNotes').value = data.notes || '';
    document.getElementById('sendReceipt').checked = data.sendReceipt || false;
    document.getElementById('createInvoice').checked = data.createInvoice || false;
}

// Функции для работы с дополнительными диагнозами
function addAdditionalDiagnosis(value = '') {
    const template = document.getElementById('additionalDiagnosisTemplate');
    const clone = template.content.cloneNode(true);
    const input = clone.querySelector('input');
    input.value = value;
    
    document.getElementById('additionalDiagnosesContainer').appendChild(clone);
}

function removeAdditionalDiagnosis(button) {
    button.closest('.additional-diagnosis-item').remove();
    saveFormData();
}

// Функции для работы с ручными назначениями
function addManualPrescription(medication = '', dosage = '', schedule = '') {
    const template = document.getElementById('manualPrescriptionTemplate');
    const clone = template.content.cloneNode(true);
    const inputs = clone.querySelectorAll('input');
    
    inputs[0].value = medication;
    inputs[1].value = dosage;
    inputs[2].value = schedule;
    
    document.getElementById('manualPrescriptionsContainer').appendChild(clone);
}

function removeManualPrescription(button) {
    button.closest('.manual-prescription-item').remove();
    saveFormData();
}

// Функции для работы с шаблонами
async function loadTemplate(templateId) {
    if (!templateId) return;
    
    try {
        const response = await fetch(`/api/medical-templates/${templateId}`);
        const template = await response.json();
        
        if (template) {
            currentTemplateId = templateId;
            
            // Заполнение диагноза
            if (template.diagnosis) {
                document.getElementById('mainDiagnosis').value = template.diagnosis.code || '';
                document.getElementById('mainDiagnosisText').value = template.diagnosis.name || '';
            }
            
            // Заполнение назначений
            loadTemplatePrescriptions(template.prescriptions);
        }
    } catch (error) {
        console.error('Ошибка загрузки шаблона:', error);
        alert('Ошибка загрузки шаблона');
    }
}

function loadTemplatePrescriptions(prescriptions) {
    const container = document.getElementById('templatePrescriptions');
    container.innerHTML = '';
    
    if (prescriptions && prescriptions.length > 0) {
        prescriptions.forEach(prescription => {
            const template = document.getElementById('templatePrescriptionItem');
            const clone = template.content.cloneNode(true);
            const checkbox = clone.querySelector('input');
            const label = clone.querySelector('label');
            
            checkbox.value = prescription;
            checkbox.checked = true;
            label.textContent = prescription;
            
            container.appendChild(clone);
        });
    }
}

function updatePaymentSummary() {
    const amount = document.getElementById('paymentAmount').value;
    const status = document.getElementById('paymentStatus').value;
    const method = document.getElementById('paymentMethod').value;
    
    // Здесь можно добавить логику для обновления сводки оплаты
    console.log('Payment updated:', { amount, status, method });
}

// Основные функции формы
async function submitForm() {
    if (!validateForm()) {
        alert('Пожалуйста, заполните обязательные поля');
        return;
    }
    
    const formData = new FormData();
    const appointmentId = document.getElementById('appointmentId').value;
    
    // Сбор данных формы
    formData.append('appointment_id', appointmentId);
    formData.append('complaints', document.getElementById('complaints').value);
    formData.append('examination', JSON.stringify(getExaminationData()));
    formData.append('diagnosis', JSON.stringify(getDiagnosisData()));
    formData.append('prescriptions', JSON.stringify(getPrescriptionsData()));
    formData.append('recommendations', document.getElementById('recommendations').value);
    formData.append('payment_amount', document.getElementById('paymentAmount').value);
    formData.append('payment_status', document.getElementById('paymentStatus').value);
    formData.append('payment_method', document.getElementById('paymentMethod').value);
    formData.append('send_to_parents', document.getElementById('sendToParents').checked);
    
    if (document.getElementById('scheduleNextVisit').checked) {
        formData.append('next_visit_date', document.getElementById('nextVisitDate').value);
        formData.append('next_visit_time', document.getElementById('nextVisitTime').value);
        formData.append('next_visit_type', document.getElementById('nextVisitType').value);
        formData.append('create_next_appointment', true);
    }
    
    try {
        const response = await fetch('/api/medical-records', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            alert('Данные визита успешно сохранены!');
            localStorage.removeItem('visitFormData'); // Очистка сохраненных данных
            window.location.href = `/appointments`; // Перенаправление к расписанию
        } else {
            throw new Error(result.message || 'Ошибка сохранения');
        }
    } catch (error) {
        console.error('Ошибка сохранения:', error);
        alert('Ошибка сохранения данных: ' + error.message);
    }
}

function saveDraft() {
    saveFormData();
    alert('Черновик сохранен');
}

function validateForm() {
    // Проверка обязательных полей
    const mainDiagnosis = document.getElementById('mainDiagnosis').value;
    if (!mainDiagnosis) {
        alert('Пожалуйста, укажите основной диагноз');
        return false;
    }
    
    const temperature = document.getElementById('temperature').value;
    if (!temperature) {
        alert('Пожалуйста, укажите температуру');
        return false;
    }
    
    return true;
}

// Вспомогательные функции
function loadAppointmentData(appointmentId) {
    // Загрузка данных о записи, если необходимо
    console.log('Loading appointment data for:', appointmentId);
}

function loadDefaultTemplates() {
    // Загрузка стандартных шаблонов при необходимости
    console.log('Loading default templates...');
}

// Функция для расчета возраста
function calculateAge(birthDate) {
    const today = new Date();
    const birth = new Date(birthDate);
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
        age--;
    }
    
    return age;
}