// Modal Management
let userConditionsModal = null;
let adminConditionsModal = null;

// Show the user conditions modal
// Show the admin conditions modal
function showAdminConditionsModal() {
    console.log('showAdminConditionsModal called');
    
    if (typeof bootstrap === 'undefined') {
        console.error('Bootstrap is not loaded');
        return;
    }
    
    const modalElement = document.getElementById('conditionsModal');
    if (!modalElement) {
        console.error('Admin conditions modal element not found');
        return;
    }
    
    if (!adminConditionsModal) {
        try {
            adminConditionsModal = new bootstrap.Modal(modalElement);
            console.log('Bootstrap Admin Modal instance created');
        } catch (error) {
            console.error('Error creating Admin Bootstrap Modal:', error);
            return;
        }
    }
    
    // Load admin conditions
    if (typeof populateAdminConditions === 'function') {
        populateAdminConditions();
    }
    
    // Show the modal
    adminConditionsModal.show();
}

// Show the user conditions modal
function showUserConditionsModal() {
    console.log('showUserConditionsModal called');
    
    // Use the globally initialized modal
    if (window.userConditionsModal) {
        window.userConditionsModal.show();
        // Load conditions when modal is shown
        populateUserConditions().catch(console.error);
    } else {
        console.error('User conditions modal not initialized');
        // Try to initialize if not already done
        window.userConditionsModal = initModal('userConditionsModal');
        if (window.userConditionsModal) {
            window.userConditionsModal.show();
            populateUserConditions().catch(console.error);
        } else {
            console.error('Failed to initialize user conditions modal');
            showToast('Failed to load conditions. Please try again.', 'error');
        }
    }
}

// Show the add condition form
function showAddConditionForm() {
    document.getElementById('user-conditions-list-view').style.display = 'none';
    document.getElementById('user-condition-form-view').style.display = 'block';
    document.getElementById('user-condition-form-title').textContent = 'Add New Condition';
    document.getElementById('user-condition-form').reset();
    document.getElementById('edit-condition-id').value = '';
    document.getElementById('user-condition-name').focus();
}

// Cancel editing and return to list view
function cancelEditCondition() {
    document.getElementById('user-conditions-list-view').style.display = 'block';
    document.getElementById('user-condition-form-view').style.display = 'none';
}

// Edit an existing condition
function editUserCondition(condition) {
    try {
        // Hide list and show form
        document.getElementById('user-conditions-list-view').style.display = 'none';
        document.getElementById('user-condition-form-view').style.display = 'block';
        document.getElementById('user-condition-form-title').textContent = 'Edit Condition';
        
        // Set form field values with proper null checks
        const form = document.getElementById('user-condition-form');
        if (form) {
            form.reset(); // Reset form first to clear any previous values
            
            // Set values for each field
            const idField = document.getElementById('edit-condition-id');
            const nameField = document.getElementById('user-condition-name');
            const linkField = document.getElementById('user-condition-link');
            const chartLinkField = document.getElementById('user-condition-chart-link');
            const clauseField = document.getElementById('user-condition-clause');
            
            if (idField) idField.value = condition.id || '';
            if (nameField) nameField.value = condition.name || '';
            if (linkField) linkField.value = condition.link || '';
            if (chartLinkField) chartLinkField.value = condition.chart_link || '';
            if (clauseField) clauseField.value = condition.scan_clause || '';
            
            // Set focus to name field
            if (nameField) nameField.focus();
        } else {
            console.error('User condition form not found');
            showToast('Error loading condition form', 'error');
        }
    } catch (error) {
        console.error('Error in editUserCondition:', error);
        showToast('Error loading condition for editing', 'error');
    }
}

// Populate user conditions
async function populateUserConditions() {
    const container = document.getElementById('user-conditions-list-container');
    if (!container) return;
    
    container.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    
    try {
        const response = await fetch('/api/user-conditions');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        const conditions = Array.isArray(data) ? data : (data.user_conditions || []);
        
        container.innerHTML = '';
        
        if (conditions.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-info-circle me-2"></i>
                    No custom conditions found. Click "Add New Condition" to create one.
                </div>`;
            return;
        }
        
        conditions.forEach(condition => {
            const div = document.createElement('div');
            div.className = 'condition-row';
            div.setAttribute('data-condition-id', condition.id);
            
            // Create a link element if chart_link exists and is not empty
            const chartLink = condition.chart_link && condition.chart_link.trim() !== '' && condition.chart_link !== '#' ? 
                `<a href="${escapeHtml(condition.chart_link)}" target="_blank" class="chart-link">
                    <i class="fas fa-external-link-alt"></i>View in Chartink
                </a>` : '';

            // Create the condition HTML with new structure
            const conditionHTML = `
                <div class="condition-content">
                    <div class="condition-name">${escapeHtml(condition.name)}</div>
                    <span class="condition-formula" title="${escapeHtml(condition.scan_clause)}">
                        ${escapeHtml(condition.scan_clause.substring(0, 100))}${condition.scan_clause.length > 100 ? '...' : ''}
                    </span>
                    ${chartLink}
                </div>
                <div class="condition-actions">
                    <button class="btn btn-outline-primary btn-sm" 
                            onclick="editUserCondition(${JSON.stringify(condition).replace(/"/g, '&quot;')}); return false;"
                            title="Edit condition">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm delete-condition" 
                            data-condition-id="${condition.id}"
                            title="Delete condition">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>`;

            div.innerHTML = conditionHTML;
            container.appendChild(div);
        });
    } catch (error) {
        console.error('Error loading user conditions:', error);
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Failed to load conditions. 
                <button class="btn btn-sm btn-outline-secondary ms-2" onclick="populateUserConditions()">
                    <i class="fas fa-sync-alt me-1"></i>Retry
                </button>
            </div>`;
    }
}

// Delete a condition
async function deleteUserCondition(conditionId, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    if (!conditionId) {
        console.error('No condition ID provided for deletion');
        showToast('Error: No condition ID provided', 'error');
        return;
    }

    if (!confirm('Are you sure you want to delete this condition? This action cannot be undone.')) {
        return;
    }

    // Get the condition element to remove
    const conditionElement = document.querySelector(`[data-condition-id="${conditionId}"]`);
    const conditionContainer = conditionElement?.closest('.list-group-item') || conditionElement;
    const conditionName = conditionElement?.querySelector('h6')?.textContent || 'this condition';
    
    // Show loading state
    const deleteButtons = document.querySelectorAll(`.delete-condition[data-condition-id="${conditionId}"]`);
    const originalButtonHTMLs = [];
    
    // Disable all delete buttons for this condition
    deleteButtons.forEach(btn => {
        originalButtonHTMLs.push(btn.innerHTML);
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Deleting...';
    });
    
    // Store the clicked button for later reference
    const originalButton = event?.target?.closest('button') || deleteButtons[0];
    const originalButtonHTML = originalButton?.innerHTML;

    try {
        console.log(`[DEBUG] Attempting to delete condition with ID: ${conditionId}`);
        
        const response = await fetch(`/api/user-conditions/${encodeURIComponent(conditionId)}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
            },
            credentials: 'same-origin'
        });

        console.log(`[DEBUG] Delete response status: ${response.status}`);
        
        let result;
        try {
            result = await response.json();
            console.log('[DEBUG] Delete response data:', result);
        } catch (parseError) {
            console.error('Error parsing delete response:', parseError);
            throw new Error('Invalid response from server');
        }

        if (!response.ok) {
            const errorMsg = result?.error || result?.message || 
                           `Failed to delete condition (${response.status} ${response.statusText})`;
            throw new Error(errorMsg);
        }

        // If we get here, the delete was successful
        console.log(`[DEBUG] Successfully deleted condition ${conditionId}`);

        // Show success message
        showToast(`Successfully deleted condition: ${conditionName}`, 'success');
        
        // Remove the condition from the UI with fade out animation
        if (conditionContainer) {
            conditionContainer.style.opacity = '0.5';
            conditionContainer.style.transition = 'opacity 0.3s';
            
            // Wait for the fade out animation to complete
            setTimeout(() => {
                conditionContainer.remove();
                
                // Check if we need to show the empty state
                const conditionsContainer = document.getElementById('user-conditions-list-container');
                if (conditionsContainer && conditionsContainer.children.length === 0) {
                    conditionsContainer.innerHTML = `
                        <div class="alert alert-info">
                            <i class="fas fa-info-circle me-2"></i>
                            No custom conditions found. Click "Add New Condition" to create one.
                        </div>`;
                }
            }, 300);
        }
        
    } catch (error) {
        console.error('Error deleting condition:', error);
        
        // Show specific error messages for common issues
        let errorMessage = 'Failed to delete condition';
        if (error.message) {
            if (error.message.includes('404')) {
                errorMessage = 'Condition not found. It may have already been deleted.';
            } else if (error.message.includes('500')) {
                errorMessage = 'Server error. Please try again later.';
            } else {
                errorMessage = error.message;
            }
        }
        
        showToast(errorMessage, 'error');
        
        // Re-enable the delete buttons
        deleteButtons.forEach((btn, index) => {
            if (originalButtonHTMLs[index]) {
                btn.disabled = false;
                btn.innerHTML = originalButtonHTMLs[index];
            }
        });
        
        // Reset button state on error
        if (originalButton && originalButtonHTML) {
            originalButton.disabled = false;
            originalButton.innerHTML = originalButtonHTML;
        }
        
        // Show more detailed error in console for debugging
        if (error instanceof Error) {
            console.error('Error details:', {
                message: error.message,
                stack: error.stack,
                name: error.name
            });
        }
    }
}

// Handle form submission
async function handleUserConditionSubmit(e) {
    // Prevent multiple submissions
    if (isSubmitting) {
        console.log('Preventing duplicate submission');
        e.preventDefault();
        return false;
    }
    isSubmitting = true;
    
    const form = e.target;
    const conditionId = document.getElementById('edit-condition-id').value;
    const isEdit = !!conditionId;
    
    // Get form elements with null checks
    const nameInput = document.getElementById('user-condition-name');
    const linkInput = document.getElementById('user-condition-link');
    const chartLinkInput = document.getElementById('user-condition-chart-link');
    const clauseInput = document.getElementById('user-condition-clause');
    
    // Prepare condition data with proper fallbacks
    const conditionData = {
        name: nameInput ? nameInput.value.trim() : '',
        link: (linkInput && linkInput.value.trim()) || '#',  // Default to '#' if empty
        chartLink: (chartLinkInput && chartLinkInput.value.trim()) || '',
        scanClause: clauseInput ? clauseInput.value.trim() : ''
    };
    
    // Convert to snake_case for backend
    const requestData = {
        name: conditionData.name,
        link: conditionData.link,
        chart_link: conditionData.chartLink,
        scan_clause: conditionData.scanClause
    };
    
    console.log('[DEBUG] Prepared request data:', requestData);
    
    // If chartLink is empty but link exists, use link as fallback
    if (!conditionData.chartLink && conditionData.link && conditionData.link !== '#') {
        conditionData.chartLink = conditionData.link;
        requestData.chart_link = conditionData.link;
    }
    
    // Validate required fields
    if (!conditionData.name) {
        showToast('Please enter a condition name', 'error');
        document.getElementById('user-condition-name').focus();
        return;
    }
    
    if (!conditionData.scan_clause) {
        showToast('Please enter a scan clause', 'error');
        document.getElementById('user-condition-clause').focus();
        return;
    }
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
    
    try {
        // First, check for duplicate names if this is a new condition
        if (!isEdit) {
            const conditions = await fetch('/api/user-conditions')
                .then(res => res.json())
                .catch(() => []);
                
            const duplicateExists = Array.isArray(conditions) && 
                conditions.some(cond => 
                    cond.name.toLowerCase() === conditionData.name.toLowerCase()
                );
                
            if (duplicateExists) {
                throw new Error('A condition with this name already exists');
            }
        }
        
        const url = isEdit 
            ? `/api/user-conditions/${conditionId}`
            : '/api/user-conditions';
        
        console.log('[DEBUG] Sending request to:', url);
        console.log('[DEBUG] Request data:', conditionData);
        
        const response = await fetch(url, {
            method: isEdit ? 'PUT' : 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
            },
            body: JSON.stringify(requestData),
            credentials: 'same-origin'  // Ensure cookies are sent
        });
        
        let result;
        try {
            result = await response.json();
            console.log('Server response:', result);
        } catch (parseError) {
            console.error('Error parsing server response:', parseError);
            throw new Error('Invalid response from server');
        }
        
        if (!response.ok) {
            const errorMsg = result.error || 
                          result.message || 
                          `Failed to ${isEdit ? 'update' : 'save'} condition (${response.status} ${response.statusText})`;
            throw new Error(errorMsg);
        }

        // If we get here, the request was successful (status 2xx)
        console.log('[DEBUG] Request successful, result:', result);
        
        // Check for success in the response
        const isSuccess = response.ok && 
                        (result?.success === true || 
                         result?.status === 'success' || 
                         !!result?.condition);
        
        if (isSuccess) {
            // Reset form and show success message
            form.reset();
            document.getElementById('user-conditions-list-view').style.display = 'block';
            document.getElementById('user-condition-form-view').style.display = 'none';
            
            // Refresh the conditions list
            await populateUserConditions();
            
            // Show success message from server or default
            showToast(
                result.message || (isEdit ? 'Condition updated successfully' : 'Condition added successfully'),
                'success'
            );
            return;
        } else {
            // Handle case where response is successful but success flag is false
            throw new Error(result?.error || 'Failed to save condition');
        }
        
    } catch (error) {
        console.error('Error saving condition:', error);
        
        // Show specific error messages for common issues
        let errorMessage = 'Failed to save condition';
        if (error.message && typeof error.message === 'string') {
            if (error.message.includes('already exists')) {
                errorMessage = 'A condition with this name already exists';
            } else if (error.message.includes('name is required')) {
                errorMessage = 'Condition name is required';
            } else if (error.message.includes('scan_clause is required')) {
                errorMessage = 'Scan clause is required';
            } else if (error.message.includes('400')) {
                errorMessage = 'Invalid request. Please check your input and try again.';
            } else if (error.message.includes('500')) {
                errorMessage = 'Server error. Please try again later.';
            }
        }
        
        showToast(errorMessage, 'error');
        
        // Re-enable the submit button if it exists
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText || 'Save Condition';
        }
    } finally {
        // Ensure button is re-enabled in case of success
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnText;
        }
    }
}

// Show toast notification
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) return;
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0 show`;
    toast.role = 'alert';
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 150);
    }, 5000);
}

// Helper function to escape HTML
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Track if form submission is in progress
let isSubmitting = false;

// Initialize event listeners when the DOM is loaded
function initializeUserConditions() {
    // Only initialize once
    if (window.userConditionsInitialized) return;
    window.userConditionsInitialized = true;
    
    // Add event delegation for delete buttons
    document.addEventListener('click', function(event) {
        const deleteButton = event.target.closest('.delete-condition');
        if (deleteButton) {
            const conditionId = deleteButton.getAttribute('data-condition-id');
            if (conditionId) {
                deleteUserCondition(conditionId, event);
            }
        }
    });
    
    console.log('Initializing user conditions...');
    
    // Initialize modals with proper error handling
    const initModal = (modalId) => {
        try {
            const modalElement = document.getElementById(modalId);
            if (!modalElement) {
                console.warn(`Modal element not found: ${modalId}`);
                return null;
            }
            
            // Check if modal is already initialized
            if (modalElement._modal) {
                return modalElement._modal;
            }
            
            // Initialize Bootstrap modal
            const modal = new bootstrap.Modal(modalElement, {
                backdrop: true,
                keyboard: true,
                focus: true
            });
            
            // Store reference to modal instance
            modalElement._modal = modal;
            
            // Add event listeners for modal events
            modalElement.addEventListener('hidden.bs.modal', function() {
                // Clean up when modal is hidden
                const form = modalElement.querySelector('form');
                if (form) {
                    form.reset();
                }
            });
            
            return modal;
        } catch (error) {
            console.error(`Error initializing modal ${modalId}:`, error);
            return null;
        }
    };
    
    // Initialize user conditions modal
    window.userConditionsModal = initModal('userConditionsModal');
    
    // Add click handler for the custom conditions button
    const customConditionsBtn = document.getElementById('customConditionsButton');
    if (customConditionsBtn && !customConditionsBtn.dataset.listenerAdded) {
        console.log('Adding click handler for custom conditions button');
        customConditionsBtn.addEventListener('click', function(e) {
            console.log('Custom conditions button clicked');
            e.preventDefault();
            e.stopPropagation();
            
            // Show the modal
            if (window.userConditionsModal) {
                window.userConditionsModal.show();
                // Load conditions when modal is shown
                populateUserConditions().catch(console.error);
            } else {
                console.error('User conditions modal not initialized');
            }
        });
        customConditionsBtn.dataset.listenerAdded = 'true';
    } else if (!customConditionsBtn) {
        console.warn('Custom conditions button not found');
    }
    
    // Add event listeners for user conditions form
    const showAddFormBtn = document.getElementById('show-add-condition-form-btn');
    const cancelEditBtn = document.getElementById('cancel-edit-condition-btn');
    const userConditionForm = document.getElementById('user-condition-form');

    if (showAddFormBtn && !showAddFormBtn.dataset.listenerAdded) {
        showAddFormBtn.addEventListener('click', showAddConditionForm);
        showAddFormBtn.dataset.listenerAdded = 'true';
    }

    if (cancelEditBtn && !cancelEditBtn.dataset.listenerAdded) {
        cancelEditBtn.addEventListener('click', cancelEditCondition);
        cancelEditBtn.dataset.listenerAdded = 'true';
    }

    if (userConditionForm && !userConditionForm.dataset.listenerAdded) {
        userConditionForm.addEventListener('submit', function(e) {
            if (isSubmitting) {
                console.log('Preventing duplicate form submission');
                e.preventDefault();
                return false;
            }
            isSubmitting = true;
            return handleUserConditionSubmit(e).finally(() => {
                isSubmitting = false;
            });
        });
        userConditionForm.dataset.listenerAdded = 'true';
    }

    // Populate conditions when modal is shown
    const userConditionsModal = document.getElementById('userConditionsModal');
    if (userConditionsModal && !userConditionsModal.dataset.listenerAdded) {
        userConditionsModal.addEventListener('show.bs.modal', function() {
            console.log('Modal shown, populating conditions...');
            populateUserConditions();
        });
        userConditionsModal.dataset.listenerAdded = 'true';
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeUserConditions);
} else {
    initializeUserConditions();
}
