// UCMS Alumni Portal JavaScript

// Screenshot Protection (for non-admin users)
function initializeScreenshotProtection() {
    // Check if user is admin (this would be set by the backend)
    const isAdmin = document.body.dataset.isAdmin === 'true';
    
    if (!isAdmin) {
        // Add screenshot protection class
        document.body.classList.add('no-screenshot');
        
        // Disable right-click context menu
        document.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            return false;
        });
        
        // Disable common screenshot shortcuts
        document.addEventListener('keydown', function(e) {
            // Disable F12, Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+U
            if (e.key === 'F12' || 
                (e.ctrlKey && e.shiftKey && (e.key === 'I' || e.key === 'J')) ||
                (e.ctrlKey && e.key === 'U') ||
                (e.metaKey && e.shiftKey && (e.key === '3' || e.key === '4'))) {
                e.preventDefault();
                showMessage('Screenshot/Developer tools are disabled for security', 'warning');
                return false;
            }
        });
        
        // Disable print screen
        document.addEventListener('keyup', function(e) {
            if (e.key === 'PrintScreen') {
                navigator.clipboard.writeText('');
                showMessage('Screenshots are not allowed', 'warning');
            }
        });
        
        // Blur content when window loses focus (when screen recording)
        let blurTimer;
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                document.body.style.filter = 'blur(5px)';
            } else {
                clearTimeout(blurTimer);
                blurTimer = setTimeout(() => {
                    document.body.style.filter = 'none';
                }, 200);
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize screenshot protection
    initializeScreenshotProtection();
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Form validation
    setupFormValidation();
    
    // Country/State/City suggestions
    setupLocationSuggestions();
    
    // OTP timer
    setupOTPTimer();
    
    // Initialize directory search behavior
    initializeDirectorySearch();
});

// Directory Search Functionality
function initializeDirectorySearch() {
    const directoryTable = document.querySelector('#directoryTable');
    const searchForm = document.querySelector('#directorySearchForm');
    const hasSearchParams = new URLSearchParams(window.location.search).toString().length > 0;
    
    // Hide all data by default, only show when searched
    if (directoryTable && !hasSearchParams) {
        const tbody = directoryTable.querySelector('tbody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-5">
                        <i class="fas fa-search fa-3x text-muted mb-3"></i>
                        <h5 class="text-muted">Use the filters above to search alumni</h5>
                        <p class="text-muted">Enter search criteria to view alumni directory</p>
                    </td>
                </tr>
            `;
        }
        
        // Update count
        const countBadge = document.querySelector('.alumni-count');
        if (countBadge) {
            countBadge.textContent = '0 Alumni (Use search to view)';
        }
    }
}

function setupFormValidation() {
    // Get all forms with validation
    var forms = document.querySelectorAll('.needs-validation');
    
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Phone number validation
    var phoneInputs = document.querySelectorAll('input[type="tel"], input[name$="contact_number"], input[name$="alternate_contact"]');
    phoneInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            validatePhoneNumber(this);
        });
    });

    // Email validation
    var emailInputs = document.querySelectorAll('input[type="email"]');
    emailInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            validateEmail(this);
        });
    });
}

function validatePhoneNumber(input) {
    var phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
    var isValid = phoneRegex.test(input.value.replace(/\s/g, ''));
    
    if (input.value && !isValid) {
        input.setCustomValidity('Please enter a valid phone number');
        input.classList.add('is-invalid');
    } else {
        input.setCustomValidity('');
        input.classList.remove('is-invalid');
    }
}

function validateEmail(input) {
    var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    var isValid = emailRegex.test(input.value);
    
    if (input.value && !isValid) {
        input.setCustomValidity('Please enter a valid email address');
        input.classList.add('is-invalid');
    } else {
        input.setCustomValidity('');
        input.classList.remove('is-invalid');
    }
}

function setupLocationSuggestions() {
    // Country suggestions
    var countryInput = document.querySelector('input[name="country"]');
    if (countryInput) {
        var countries = [
            'Afghanistan', 'Albania', 'Algeria', 'Argentina', 'Australia', 'Austria',
            'Bangladesh', 'Belgium', 'Brazil', 'Canada', 'China', 'Denmark',
            'Egypt', 'France', 'Germany', 'India', 'Indonesia', 'Iran',
            'Italy', 'Japan', 'Malaysia', 'Netherlands', 'Pakistan', 'Russia',
            'Saudi Arabia', 'Singapore', 'South Africa', 'Spain', 'Switzerland',
            'Thailand', 'Turkey', 'United Kingdom', 'United States'
        ];
        setupAutoComplete(countryInput, countries);
    }

    // State suggestions (for India)
    var stateInput = document.querySelector('input[name="state"]');
    if (stateInput) {
        var indianStates = [
            'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
            'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand',
            'Karnataka', 'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur',
            'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab',
            'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura',
            'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Delhi'
        ];
        setupAutoComplete(stateInput, indianStates);
    }
}

function setupAutoComplete(input, suggestions) {
    var currentFocus = -1;
    
    input.addEventListener('input', function() {
        var val = this.value;
        closeAllLists();
        
        if (!val) return false;
        
        var listDiv = document.createElement('div');
        listDiv.setAttribute('id', this.id + '-autocomplete-list');
        listDiv.setAttribute('class', 'autocomplete-items');
        this.parentNode.appendChild(listDiv);
        
        for (var i = 0; i < suggestions.length; i++) {
            if (suggestions[i].substr(0, val.length).toUpperCase() === val.toUpperCase()) {
                var itemDiv = document.createElement('div');
                itemDiv.innerHTML = '<strong>' + suggestions[i].substr(0, val.length) + '</strong>';
                itemDiv.innerHTML += suggestions[i].substr(val.length);
                itemDiv.innerHTML += '<input type="hidden" value="' + suggestions[i] + '">';
                
                itemDiv.addEventListener('click', function() {
                    input.value = this.getElementsByTagName('input')[0].value;
                    closeAllLists();
                });
                
                listDiv.appendChild(itemDiv);
            }
        }
    });
    
    input.addEventListener('keydown', function(e) {
        var list = document.getElementById(this.id + '-autocomplete-list');
        if (list) {
            var items = list.getElementsByTagName('div');
            if (e.keyCode === 40) { // Down
                currentFocus++;
                addActive(items);
            } else if (e.keyCode === 38) { // Up
                currentFocus--;
                addActive(items);
            } else if (e.keyCode === 13) { // Enter
                e.preventDefault();
                if (currentFocus > -1) {
                    if (items) items[currentFocus].click();
                }
            }
        }
    });
    
    function addActive(items) {
        if (!items) return false;
        removeActive(items);
        if (currentFocus >= items.length) currentFocus = 0;
        if (currentFocus < 0) currentFocus = (items.length - 1);
        items[currentFocus].classList.add('autocomplete-active');
    }
    
    function removeActive(items) {
        for (var i = 0; i < items.length; i++) {
            items[i].classList.remove('autocomplete-active');
        }
    }
    
    function closeAllLists(elmnt) {
        var items = document.getElementsByClassName('autocomplete-items');
        for (var i = 0; i < items.length; i++) {
            if (elmnt !== items[i] && elmnt !== input) {
                items[i].parentNode.removeChild(items[i]);
            }
        }
    }
    
    document.addEventListener('click', function(e) {
        closeAllLists(e.target);
    });
}

function setupOTPTimer() {
    var otpTimer = document.querySelector('.otp-timer');
    if (otpTimer) {
        var timeLeft = 300; // 5 minutes
        var timer = setInterval(function() {
            var minutes = Math.floor(timeLeft / 60);
            var seconds = timeLeft % 60;
            otpTimer.textContent = 'OTP expires in ' + minutes + ':' + (seconds < 10 ? '0' : '') + seconds;
            
            if (timeLeft <= 0) {
                clearInterval(timer);
                otpTimer.textContent = 'OTP expired. Please request a new one.';
                otpTimer.style.color = 'red';
            }
            timeLeft--;
        }, 1000);
    }
}

// Utility functions
function showLoading(element) {
    element.classList.add('loading');
    var loadingSpinner = document.createElement('i');
    loadingSpinner.className = 'fas fa-spinner fa-spin';
    element.appendChild(loadingSpinner);
}

function hideLoading(element) {
    element.classList.remove('loading');
    var spinner = element.querySelector('.fa-spinner');
    if (spinner) {
        spinner.remove();
    }
}

function showMessage(message, type = 'info') {
    var messageContainer = document.querySelector('.message-container');
    if (!messageContainer) {
        messageContainer = document.createElement('div');
        messageContainer.className = 'message-container position-fixed';
        messageContainer.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
        document.body.appendChild(messageContainer);
    }
    
    var alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show shadow`;
    alert.style.cssText = 'margin-bottom: 10px; animation: slideInRight 0.3s ease-out;';
    alert.innerHTML = `
        <i class="fas fa-${type === 'warning' ? 'exclamation-triangle' : type === 'success' ? 'check-circle' : 'info-circle'}"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    messageContainer.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(function() {
        if (alert.parentNode) {
            alert.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.parentNode.removeChild(alert);
                }
            }, 300);
        }
    }, 5000);
}

// AJAX helper function
function makeRequest(url, method = 'GET', data = null) {
    return new Promise(function(resolve, reject) {
        var xhr = new XMLHttpRequest();
        xhr.open(method, url);
        xhr.setRequestHeader('Content-Type', 'application/json');
        
        // Add CSRF token for POST requests
        if (method === 'POST') {
            var csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
            if (csrfToken) {
                xhr.setRequestHeader('X-CSRFToken', csrfToken.value);
            }
        }
        
        xhr.onload = function() {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    var response = JSON.parse(xhr.responseText);
                    resolve(response);
                } catch (e) {
                    resolve(xhr.responseText);
                }
            } else {
                reject(new Error('Request failed: ' + xhr.status));
            }
        };
        
        xhr.onerror = function() {
            reject(new Error('Network error'));
        };
        
        if (data) {
            xhr.send(JSON.stringify(data));
        } else {
            xhr.send();
        }
    });
}

// Photo preview function
function previewPhoto(input) {
    if (input.files && input.files[0]) {
        var reader = new FileReader();
        reader.onload = function(e) {
            var preview = document.querySelector('#photo-preview');
            if (!preview) {
                preview = document.createElement('img');
                preview.id = 'photo-preview';
                preview.style.maxWidth = '150px';
                preview.style.maxHeight = '150px';
                preview.style.marginTop = '10px';
                preview.style.borderRadius = '50%';
                input.parentNode.appendChild(preview);
            }
            preview.src = e.target.result;
        };
        reader.readAsDataURL(input.files[0]);
    }
}

// Add photo preview to file inputs
document.addEventListener('DOMContentLoaded', function() {
    var photoInputs = document.querySelectorAll('input[type="file"][name="photo"]');
    photoInputs.forEach(function(input) {
        input.addEventListener('change', function() {
            previewPhoto(this);
        });
    });
});

// Enhanced Alumni Details Modal
function viewAlumniDetails(alumniId) {
    // Show loading state
    const modal = new bootstrap.Modal(document.getElementById('alumniDetailsModal'));
    const content = document.getElementById('alumniDetailsContent');
    
    content.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3">Loading alumni details...</p>
        </div>
    `;
    
    modal.show();
    
    // In a real implementation, fetch alumni details via AJAX
    setTimeout(() => {
        content.innerHTML = `
            <div class="row">
                <div class="col-md-4 text-center">
                    <div class="profile-photo-placeholder mb-3">
                        <i class="fas fa-user fa-4x"></i>
                    </div>
                    <h5>Alumni Profile</h5>
                </div>
                <div class="col-md-8">
                    <p><strong>Alumni ID:</strong> ${alumniId}</p>
                    <p><strong>Note:</strong> Detailed alumni information is protected for privacy.</p>
                    <p class="text-muted">Only basic information is shown in the directory.</p>
                </div>
            </div>
        `;
    }, 1000);
}

// Amazing Registration Page Functionality
let currentStep = 1;
let otpTimer;
let timeLeft = 300; // 5 minutes in seconds
let registrationData = {};

// Initialize registration page
function initializeRegistration() {
    if (document.querySelector('.modern-registration-container')) {
        setupPhotoUpload();
        setupStepNavigation();
        setupFormValidation();
        activateStep(1);
        
        // Handle form submission
        const form = document.getElementById('registrationForm');
        if (form) {
            form.addEventListener('submit', handleRegistrationSubmit);
        }
    }
}

// Setup photo upload functionality
function setupPhotoUpload() {
  const photoInput = document.getElementById('id_photo');
  const photoPreview = document.getElementById('photoPreview');

  // Only continue if not already bound
  if (!photoInput || !photoPreview || photoPreview.dataset.bound === 'true') return;

  // Mark as bound to prevent multiple triggers
  photoPreview.dataset.bound = 'true';

  const imgElement = photoPreview.querySelector('img');

  // ✅ When preview is clicked, open file dialog once
  photoPreview.addEventListener('click', () => {
    photoInput.click();
  });

  // ✅ When a file is chosen, update preview image
  photoInput.addEventListener('change', function (e) {
    const file = e.target.files[0];
    const maxSizeKB = 300;
  
    if (file) {
      if (!file.type.startsWith('image/')) {
        alert('Please select a valid image file');
        photoInput.value = '';
        return;
      }
  
      const fileSizeKB = file.size / 1024;
      if (fileSizeKB > maxSizeKB) {
        alert('Image size must be under 300 KB');
        photoInput.value = '';
        return;
      }
  
      const reader = new FileReader();
      reader.onload = function (e) {
        imgElement.src = e.target.result;
      };
      reader.readAsDataURL(file);
    }
  });
  
}




// Setup step navigation
function setupStepNavigation() {
    const steps = document.querySelectorAll('.registration-step');
    steps.forEach((step, index) => {
        if (index === 0) {
            step.style.display = 'block';
        } else {
            step.style.display = 'none';
        }
    });
}

// Activate specific step
function activateStep(stepNumber) {
    currentStep = stepNumber;
    
    // Update progress indicators
    const progressSteps = document.querySelectorAll('.progress-step');
    progressSteps.forEach((step, index) => {
        if (index + 1 <= stepNumber) {
            step.classList.add('active');
        } else {
            step.classList.remove('active');
        }
    });
    
    // Update progress lines
    const progressLines = document.querySelectorAll('.progress-line');
    progressLines.forEach((line, index) => {
        if (index + 1 < stepNumber) {
            line.style.setProperty('--progress', '100%');
            line.querySelector('::after')?.style.setProperty('width', '100%');
        } else {
            line.style.setProperty('--progress', '0%');
        }
    });
    
    // Show/hide steps
    const steps = document.querySelectorAll('.registration-step');
    steps.forEach((step, index) => {
        if (index + 1 === stepNumber) {
            step.style.display = 'block';
            step.style.animation = 'fadeInUp 0.5s ease-out';
        } else {
            step.style.display = 'none';
        }
    });
}

// Setup form validation
function setupFormValidation() {
    const inputs = document.querySelectorAll('.input-container input, .input-container select');
    inputs.forEach(input => {
        input.addEventListener('blur', validateField);
        input.addEventListener('input', clearFieldError);
    });
}

// Validate individual field
function validateField(e) {
    const field = e.target;
    const container = field.closest('.input-container');
    const isRequired = field.hasAttribute('required');
    
    // Remove existing error styling
    container.classList.remove('error');
    
    if (isRequired && !field.value.trim()) {
        container.classList.add('error');
        return false;
    }
    
    // Email validation
    if (field.type === 'email' && field.value) {
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailPattern.test(field.value)) {
            container.classList.add('error');
            return false;
        }
    }
    
    // Phone validation
    if (field.name === 'contact_number' && field.value) {
        const phonePattern = /^[\+]?[1-9][\d]{0,15}$/;
        if (!phonePattern.test(field.value.replace(/[\s\-\(\)]/g, ''))) {
            container.classList.add('error');
            return false;
        }
    }
    
    return true;
}

// Clear field error
function clearFieldError(e) {
    const field = e.target;
    const container = field.closest('.input-container');
    container.classList.remove('error');
}

// Handle registration form submission
function handleRegistrationSubmit(e) {
    e.preventDefault();
    // Don't submit yet, just proceed to verification
    proceedToVerification();
}

// Proceed to verification step
function proceedToVerification() {
    console.log("Proceed to verification triggered");

    // Validate all required fields
    const form = document.getElementById('registrationForm');
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!validateField({target: field})) {
            isValid = false;
        }
    });

    
    // Check declaration checkbox
    const declaration = document.getElementById('id_declaration');
    if (!declaration.checked) {
        showMessage('Please accept the declaration to proceed', 'warning');
        declaration.focus();
        return;
    }
    
    if (!isValid) {
        showMessage('Please fill in all required fields correctly', 'error');
        return;
    }

    
  // Store form data
  const formData = new FormData(form);
  registrationData = Object.fromEntries(formData);

  // Send OTP
  sendRegistrationOTP();

  // Move to verification step
  activateStep(2);
  startOTPTimer();
}
// Function to activate the verification step
function activateStep(stepNumber) {
    // Hide all steps
    const steps = document.querySelectorAll('.registration-step');
    steps.forEach(step => {
        step.style.display = 'none';
    });

    // Show the step corresponding to the stepNumber
    const currentStep = document.getElementById(`step${stepNumber}`);
    if (currentStep) {
        currentStep.style.display = 'block';
    }
}

// Simple validation function (optional)
function validateField(e) {
    const field = e.target;
    if (!field.value.trim()) {
        field.classList.add('error');
        return false;
    }
    field.classList.remove('error');
    return true;
}
// Send OTP for registration
function sendRegistrationOTP() {
    const contactNumber = document.querySelector('[name="contact_number"]').value;
    const email = document.querySelector('[name="email"]').value;
    
    // Show loading state
    showMessage('Sending OTP codes...', 'info');
    
    // Simulate OTP sending (in real implementation, this would be an API call)
    setTimeout(() => {
        showMessage('OTP codes sent successfully!', 'success');
        console.log(`OTP sent to ${contactNumber} and ${email}`);
    }, 1000);
}

// Start OTP timer
function startOTPTimer() {
    timeLeft = 300; // Reset to 5 minutes
    const timerElement = document.getElementById('otpTimer');
    
    otpTimer = setInterval(() => {
        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;
        const display = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        
        if (timerElement) {
            timerElement.textContent = `OTP expires in ${display}`;
        }
        
        if (timeLeft <= 0) {
            clearInterval(otpTimer);
            if (timerElement) {
                timerElement.textContent = 'OTP expired';
                timerElement.style.color = '#dc3545';
            }
            disableOTPInputs();
        }
        
        timeLeft--;
    }, 1000);
}

// Disable OTP inputs when expired
function disableOTPInputs() {
    const otpInputs = document.querySelectorAll('.otp-input');
    otpInputs.forEach(input => {
        input.disabled = true;
        input.style.opacity = '0.5';
    });
}

// Resend OTP
function resendOTP(type) {
    if (otpTimer) {
        clearInterval(otpTimer);
    }
    
    showMessage(`Resending OTP to ${type}...`, 'info');
    
    // Simulate resending (in real implementation, this would be an API call)
    setTimeout(() => {
        showMessage(`OTP resent to ${type} successfully!`, 'success');
        startOTPTimer();
        
        // Re-enable inputs
        const otpInputs = document.querySelectorAll('.otp-input');
        otpInputs.forEach(input => {
            input.disabled = false;
            input.style.opacity = '1';
        });
    }, 1000);
}

// Go back to form
function goBackToForm() {
    if (otpTimer) {
        clearInterval(otpTimer);
    }
    activateStep(1);
}

// Complete registration
function completeRegistration() {
    const phoneOtp = document.getElementById('phoneOtp').value;
    const emailOtp = document.getElementById('emailOtp').value;
    
    if (!phoneOtp || phoneOtp.length !== 6) {
        showMessage('Please enter valid phone OTP', 'warning');
        document.getElementById('phoneOtp').focus();
        return;
    }
    
    if (!emailOtp || emailOtp.length !== 6) {
        showMessage('Please enter valid email OTP', 'warning');
        document.getElementById('emailOtp').focus();
        return;
    }
    
    // Show loading
    showMessage('Verifying OTP and completing registration...', 'info');
    
    // Simulate verification and registration (in real implementation, this would submit to server)
    setTimeout(() => {
        if (otpTimer) {
            clearInterval(otpTimer);
        }
        
        // Submit the form data to server
        submitRegistrationData();
        
        // Move to success step
        activateStep(3);
    }, 2000);
}

// Submit registration data to server
function submitRegistrationData() {
    const form = document.getElementById('registrationForm');
    const formData = new FormData(form);
    
    // In real implementation, this would submit to the Django backend
    fetch(form.action || '/register/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Registration completed successfully');
        } else {
            showMessage('Registration failed. Please try again.', 'error');
            goBackToForm();
        }
    })
    .catch(error => {
        console.error('Registration error:', error);
        // For now, we'll continue to success step anyway
    });
}

// Add CSS for field validation
const validationStyles = `
.input-container.error input,
.input-container.error select {
    border-color: #dc3545 !important;
    box-shadow: 0 0 0 3px rgba(220, 53, 69, 0.1) !important;
}

.input-container.error .input-icon {
    color: #dc3545 !important;
}

@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.progress-line::after {
    width: var(--progress, 0%);
}
`;

// Add styles to document
if (!document.getElementById('validation-styles')) {
    const style = document.createElement('style');
    style.id = 'validation-styles';
    style.textContent = validationStyles;
    document.head.appendChild(style);
}

// Initialize registration when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeRegistration();
});
