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
    console.log('[UserConditions] Canceling edit condition');
    document.getElementById('user-conditions-list-view').style.display = 'block';
    document.getElementById('user-condition-form-view').style.display = 'none';
}

// Edit an existing condition
function editUserCondition(condition) {
    console.log('[UserConditions] Starting to edit condition:', JSON.stringify(condition, null, 2));
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

// Show the condition form
function showConditionForm() {
    console.log('[UserConditions] Showing condition form');
    const formView = document.getElementById('user-condition-form-view');
    const listView = document.getElementById('user-conditions-list-view');
    
    if (formView && listView) {
        formView.style.display = 'block';
        listView.style.display = 'none';
        document.getElementById('condition-name').focus();
        console.log('[UserConditions] Form shown, list view hidden');
    } else {
        console.error('[UserConditions] Could not find form or list view elements');
    }
}

// Hide the condition form
function hideConditionForm() {
    console.log('[UserConditions] Hiding condition form');
    const form = document.getElementById('user-condition-form');
    const formView = document.getElementById('user-condition-form-view');
    const listView = document.getElementById('user-conditions-list-view');
    
    if (form && formView && listView) {
        form.reset();
        document.getElementById('edit-condition-id').value = '';
        formView.style.display = 'none';
        listView.style.display = 'block';
        console.log('[UserConditions] Form hidden, list view shown');
    } else {
        console.error('[UserConditions] Could not find form elements to hide');
    }
}

// Initialize the modal when it's shown
document.addEventListener('DOMContentLoaded', function() {
    const userConditionsModal = document.getElementById('userConditionsModal');
    if (userConditionsModal) {
        userConditionsModal.addEventListener('show.bs.modal', function() {
            populateUserConditions();
        });
    }
});

// Populate user conditions
async function populateUserConditions() {
    const container = document.getElementById('user-conditions-list-container');
    if (!container) {
        console.error('User conditions container not found');
        return;
    }
    
    // Show loading state
    container.innerHTML = `
        <div class="d-flex justify-content-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>`;
    
    try {
        console.log('Fetching user conditions...');
        // Add timestamp to prevent caching
        const timestamp = new Date().getTime();
        const response = await fetch(`/api/user-conditions?_=${timestamp}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            },
            credentials: 'same-origin',
            cache: 'no-store'
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('User conditions data:', data);
        
        // Handle both array and object response formats
        const conditions = Array.isArray(data) ? data : (data.user_conditions || []);
        
        // Clear container
        container.innerHTML = '';
        
        if (conditions.length === 0) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    No custom conditions found. Click "Add New Condition" to create one.
                </div>`;
            return;
        }
        
        // Create a form for saving selections
        const form = document.createElement('form');
        form.id = 'user-conditions-form';
        
        // Add a save button at the top
        const saveButton = document.createElement('button');
        saveButton.type = 'submit';
        saveButton.className = 'btn btn-primary mb-3';
        saveButton.innerHTML = '<i class="fas fa-save me-1"></i> Save Selections';
        form.appendChild(saveButton);
        
        // Create a list group for the conditions
        const listGroup = document.createElement('div');
        listGroup.className = 'list-group list-group-flush mb-3';
        
        // Add each condition to the list
        conditions.forEach(condition => {
            const conditionId = condition.id;
            const conditionName = condition.name || 'Unnamed Condition';
            const scanClause = condition.scan_clause || '';
            const chartLink = condition.chart_link || '';
            
            // Create condition item
            const conditionItem = document.createElement('div');
            conditionItem.className = 'list-group-item d-flex justify-content-between align-items-center py-2';
            conditionItem.setAttribute('data-condition-id', conditionId);
            
            // Create checkbox
            const checkboxDiv = document.createElement('div');
            checkboxDiv.className = 'form-check me-2';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'form-check-input condition-checkbox me-2';
            checkbox.id = `condition-${conditionId}`;
            checkbox.checked = true; // Default to checked
            
            const label = document.createElement('label');
            label.className = 'form-check-label';
            label.htmlFor = `condition-${conditionId}`;
            
            checkboxDiv.appendChild(checkbox);
            checkboxDiv.appendChild(label);
            
            // Create condition content
            const conditionContent = document.createElement('div');
            conditionContent.className = 'flex-grow-1 ms-2';
            
            const nameElement = document.createElement('h6');
            nameElement.className = 'mb-1';
            nameElement.textContent = conditionName;
            
            const clauseElement = document.createElement('div');
            clauseElement.className = 'text-muted small text-truncate';
            clauseElement.textContent = scanClause;
            clauseElement.title = scanClause;
            clauseElement.style.maxWidth = '500px';
            
            conditionContent.appendChild(nameElement);
            conditionContent.appendChild(clauseElement);
            
            // Create action buttons
            const buttonGroup = document.createElement('div');
            buttonGroup.className = 'btn-group btn-group-sm';
            
            // Edit button
            const editButton = document.createElement('button');
            editButton.className = 'btn btn-outline-primary';
            editButton.innerHTML = '<i class="fas fa-edit"></i>';
            editButton.title = 'Edit condition';
            editButton.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                editUserCondition(condition);
            };
            
            // Delete button
            const deleteButton = document.createElement('button');
            deleteButton.className = 'btn btn-outline-danger delete-condition';
            deleteButton.innerHTML = '<i class="fas fa-trash"></i>';
            deleteButton.title = 'Delete condition';
            deleteButton.setAttribute('data-condition-id', conditionId);
            deleteButton.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                deleteUserCondition(conditionId, e);
            };
            
            // Add buttons to button group
            buttonGroup.appendChild(editButton);
            buttonGroup.appendChild(deleteButton);
            
            // Add elements to condition item
            conditionItem.appendChild(checkboxDiv);
            conditionItem.appendChild(conditionContent);
            conditionItem.appendChild(buttonGroup);
            
            // Add condition item to list group
            listGroup.appendChild(conditionItem);
        });
        
        // Add list group and form to container
        form.appendChild(listGroup);
        container.appendChild(form);
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

// Helper: Bootstrap confirmation dialog returns Promise<boolean>
async function showConfirmDialog(message = 'Are you sure?') {
    // Create modal lazily
    let modalEl = document.getElementById('confirmDeleteModal');
    if (!modalEl) {
        modalEl = document.createElement('div');
        modalEl.innerHTML = `
        <div class="modal fade" id="confirmDeleteModal" tabindex="-1" aria-labelledby="confirmDeleteModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="confirmDeleteModalLabel">Confirm Delete</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p id="confirmDeleteMessage"></p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" id="confirmNoBtn">Cancel</button>
                        <button type="button" class="btn btn-danger" id="confirmYesBtn">Delete</button>
                    </div>
                </div>
            </div>
        </div>`;
        document.body.appendChild(modalEl);
    }

    // Update message
    modalEl.querySelector('#confirmDeleteMessage').textContent = message;

    const bsModal = new bootstrap.Modal(modalEl);

    return new Promise((resolve) => {
        const yesBtn = modalEl.querySelector('#confirmYesBtn');
        const noBtn = modalEl.querySelector('#confirmNoBtn');

        // --- Helper to clean listener references ---
        const cleanup = () => {
            yesBtn.removeEventListener('click', onYes);
            noBtn.removeEventListener('click', onNo);
            modalEl.removeEventListener('hidden.bs.modal', onHidden);
        };

        // Properly dispose the modal and backdrop once fully hidden
        const disposeModal = () => {
            try {
                bsModal.dispose();
            } catch (_) {}
            if (modalEl && modalEl.parentNode) {
                modalEl.parentNode.removeChild(modalEl);
            }
            // Remove any stray backdrop or body class in case Bootstrap missed it
            const backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) backdrop.remove();
            document.body.classList.remove('modal-open');
            // Notify any global timer/listener that all modals are closed
            document.dispatchEvent(new Event('allModalsClosed'));
        };

        const onYes = () => {
            cleanup();
            bsModal.hide();
            resolve(true);
        };

        const onNo = () => {
            cleanup();
            bsModal.hide();
            resolve(false);
        };

        const onHidden = () => {
            disposeModal();
        };

        yesBtn.addEventListener('click', onYes);
        noBtn.addEventListener('click', onNo);
        modalEl.addEventListener('hidden.bs.modal', onHidden);

        bsModal.show();
    });
}

// Delete a condition immediately without confirmation
async function deleteUserCondition(conditionId, event) {
    console.debug('[UserConditions] Delete initiated for condition ID:', conditionId);
    
    // Prevent multiple submissions
    if (isSubmitting) {
        console.log('[UserConditions] Preventing duplicate delete submission');
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        return;
    }
    
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    // Identify the element and condition name
    const conditionElement = document.querySelector(`[data-condition-id="${conditionId}"]`);
    const conditionContainer = conditionElement?.closest('.list-group-item') || conditionElement;
    const conditionName = conditionElement?.querySelector('h6')?.textContent || 'this condition';

    // Use a class-based approach to track deletion state
    if (conditionElement?.classList.contains('deleting')) return;
    conditionElement?.classList.add('deleting');

    if (!conditionId) {
        console.error('No condition ID provided for deletion');
        showToast('Error: No condition ID provided', 'error');
        isSubmitting = false;
        return;
    }
    
    // Show loading state
    const deleteButtons = document.querySelectorAll(`.delete-condition[data-condition-id="${conditionId}"]`);
    const originalButtonHTMLs = [];
    
    // Disable all delete buttons for this condition
    deleteButtons.forEach(btn => {
        originalButtonHTMLs.push(btn.innerHTML);
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Deleting...';
    });
    
    try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
        const response = await fetch(`/api/user-conditions/${conditionId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            credentials: 'same-origin'
        });
        
        let result;
        try {
            result = await response.json();
            console.log('[UserConditions] API response data:', result);
        } catch (parseError) {
            console.error('[UserConditions] Error parsing JSON response:', parseError);
            const textResponse = await response.text();
            console.error('[UserConditions] Raw response text:', textResponse.substring(0, 500));
            throw new Error(`Invalid response from server: ${parseError.message}`);
        }
        
        if (!response.ok || (result && result.success === false)) {
            const errorMsg = result?.error || result?.message || `HTTP error! status: ${response.status}`;
            console.error('[UserConditions] API error response:', {
                status: response.status,
                statusText: response.statusText,
                error: errorMsg,
                response: result
            });
            throw new Error(errorMsg);
        }

        // If we get here, the delete was successful
        console.log(`Successfully deleted condition ${conditionId}`);

        // Show success message
        showToast(result?.message || `Successfully deleted condition: ${conditionName}`, 'success');
        
        // Force reload the conditions list from server
        console.log('[UserConditions] Refreshing conditions list after delete');
        
        // Clear the container first
        const container = document.getElementById('user-conditions-list-container');
        if (conditionContainer) {
            conditionContainer.style.transition = 'opacity 0.3s';
            conditionContainer.style.opacity = '0';
            setTimeout(() => {
                conditionContainer.remove();
                // Check if we need to show the empty state
                const container = document.querySelector('#user-conditions-list-container');
                if (container && container.children.length === 0) {
                    container.innerHTML = `
                        <div class="alert alert-info">
                            No conditions found. Click "Add New Condition" to create one.
                        </div>`;
                }
            }, 300);
        } else {
            // Fallback to refresh if we can't find the container
            await populateUserConditions();
        }
        
        return true;
        
    } catch (error) {
        console.error('Error deleting condition:', error);
        showToast(`Error: ${error.message}`, 'error');
        
        // Reset the deletion state on error
        conditionElement?.classList.remove('deleting');
        
        // Re-enable the delete buttons
        const deleteButtons = document.querySelectorAll(`.delete-condition[data-condition-id="${conditionId}"]`);
        deleteButtons.forEach(btn => {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-trash"></i>';
        });
        
        return false;
    }
}
