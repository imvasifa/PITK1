// --- Guard all user-conditions modal/loader logic ---
(function() {
    // Only run if the user conditions modal or container exists
    const modalExists = document.getElementById('userConditionsModal');
    const containerExists = document.getElementById('user-conditions-list-container');
    if (!modalExists && !containerExists) {
        // Do not run any user-conditions logic on this page
        return;
    }

    // --- All user-conditions code below this line is now guarded ---
    // Modal Management
    let userConditionsModal = null;
    let adminConditionsModal = null;

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

    // Delete a condition
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
    if (!confirmed) return;

    // Set submitting flag only after user confirmed
    isSubmitting = true;

    if (!conditionId) {
        console.error('No condition ID provided for deletion');
        showToast('Error: No condition ID provided', 'error');
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
    
    // Store the clicked button for later reference
    const originalButton = event?.target?.closest('button') || deleteButtons[0];
    const originalButtonHTML = originalButton?.innerHTML;

    try {
        console.log(`Attempting to delete condition with ID: ${conditionId}`);
        
        // Get CSRF token from meta tag
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
        
        const response = await fetch(`/api/user-conditions/${encodeURIComponent(conditionId)}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        });

        console.log(`Delete response status: ${response.status}`);
        
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
        if (container) {
            container.innerHTML = `
                <div class="d-flex justify-content-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>`;
        }
        
        // Force reload the conditions
        await populateUserConditions();
        
        // Remove the condition from the UI with fade out animation
        if (conditionContainer) {
            conditionContainer.style.opacity = '0';
            conditionContainer.style.transition = 'opacity 0.3s ease';
            
            // Wait for the fade out animation to complete
            setTimeout(() => {
                conditionContainer.remove();
                
                // Check if we need to show the empty state
                const conditionsContainer = document.getElementById('user-conditions-list-container');
                const noConditionsMessage = document.getElementById('no-conditions-message');
                
                if (conditionsContainer && conditionsContainer.children.length === 0) {
                    if (noConditionsMessage) {
                        noConditionsMessage.style.display = 'block';
                    } else {
                        conditionsContainer.innerHTML = `
                            <div class="alert alert-info" id="no-conditions-message">
                                <i class="fas fa-info-circle me-2"></i>
                                No custom conditions found. Click "Add New Condition" to create one.
                            </div>`;
                    }
                }
            }, 300);
        }
        
        return true;
        
    } catch (error) {
        console.error('[UserConditions] Error deleting condition:', error);
        
        // Show detailed error message
        let errorMessage = 'Failed to delete condition';
        if (error.message) {
            if (error.message.includes('NetworkError')) {
                errorMessage = 'Network error. Please check your connection and try again.';
            } else if (error.message.includes('404') || error.message.toLowerCase().includes('not found')) {
                errorMessage = 'Condition not found. It may have already been deleted.';
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
        
        // Reset submitting flag and button state on error
        if (originalButton && originalButtonHTML) {
            originalButton.disabled = false;
            originalButton.innerHTML = originalButtonHTML;
        }
        
        return false;
    }
}

// Handle form submission
async function handleUserConditionSubmit(e) {
    console.log('[UserConditions] Form submission started');
    // Prevent multiple submissions
    if (isSubmitting) {
        console.log('[UserConditions] Preventing duplicate submission');
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
    
    console.log('[UserConditions] Form inputs:', {
        nameInput: nameInput ? 'found' : 'not found',
        linkInput: linkInput ? 'found' : 'not found',
        chartLinkInput: chartLinkInput ? 'found' : 'not found',
        clauseInput: clauseInput ? 'found' : 'not found'
    });
    
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
    
    console.log('[UserConditions] Form data prepared:', {
        isEdit: !!conditionId,
        conditionId: conditionId || 'new',
        conditionData: {
            ...conditionData,
            scanClause: conditionData.scanClause ? `${conditionData.scanClause.substring(0, 50)}...` : 'empty'
        },
        requestData: {
            ...requestData,
            scan_clause: requestData.scan_clause ? `${requestData.scan_clause.substring(0, 50)}...` : 'empty'
        }
    });
    
    // If chartLink is empty but link exists, use link as fallback
    if (!conditionData.chartLink && conditionData.link && conditionData.link !== '#') {
        conditionData.chartLink = conditionData.link;
        requestData.chart_link = conditionData.link;
    }
    
    // Validate required fields
    if (!conditionData.name) {
        const errorMsg = 'Please enter a condition name';
        console.error('[UserConditions] Validation failed:', errorMsg);
        showToast(errorMsg, 'error');
        document.getElementById('user-condition-name')?.focus();
        isSubmitting = false;
        return false;
    }
    
    if (!conditionData.scanClause) {
        const errorMsg = 'Please enter a scan clause';
        console.error('[UserConditions] Validation failed:', errorMsg);
        showToast(errorMsg, 'error');
        document.getElementById('user-condition-clause')?.focus();
        isSubmitting = false;
        return false;
    }
    
    // Show loading state
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
    
    try {
        console.log('[UserConditions] Starting form submission...');
        
        // First, check for duplicate names if this is a new condition
        if (!isEdit) {
            console.log('[UserConditions] Checking for duplicate condition names...');
            const response = await fetch('/api/user-conditions');
            const conditions = await response.json().catch(() => []);
            
            console.log('[UserConditions] Existing conditions:', conditions);
            
            const duplicateExists = Array.isArray(conditions) && 
                conditions.some(cond => 
                    cond.name.toLowerCase() === conditionData.name.toLowerCase()
                );
                
            if (duplicateExists) {
                const errorMsg = `A condition with the name "${conditionData.name}" already exists`;
                console.error('[UserConditions] Duplicate condition found:', errorMsg);
                throw new Error(errorMsg);
            }
        }
        
        // Prepare the API request
        const url = isEdit ? `/api/user-conditions/${conditionId}` : '/api/user-conditions';
        const method = isEdit ? 'PUT' : 'POST';
        
        console.log('[UserConditions] Sending API request:', {
            method,
            url,
            isEdit,
            conditionId: conditionId || 'new',
            requestData: {
                ...requestData,
                scan_clause: requestData.scan_clause ? `${requestData.scan_clause.substring(0, 50)}...` : 'empty'
            }
        });
        
        const startTime = Date.now();
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || '',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(requestData),
            credentials: 'same-origin'
        });
        
        const responseTime = Date.now() - startTime;
        
        // Clone the response to read it multiple times if needed
        const responseClone = response.clone();
        
        console.log(`[UserConditions] API response received in ${responseTime}ms`, {
            status: response.status,
            statusText: response.statusText,
            url: response.url
        });
        
        // Try to parse response as JSON
        let result;
        try {
            result = await response.json();
            console.log('[UserConditions] API response data:', {
                ...result,
                // Truncate large data in logs
                scan_clause: result.scan_clause ? `${result.scan_clause.substring(0, 50)}...` : 'empty'
            });
        } catch (parseError) {
            console.error('[UserConditions] Error parsing JSON response:', parseError);
            const textResponse = await responseClone.text();
            console.error('[UserConditions] Raw response text:', textResponse.substring(0, 500));
            throw new Error(`Invalid response from server: ${parseError.message}`);
        }
        
        if (!response.ok) {
            const errorMsg = result?.message || `HTTP error! status: ${response.status}`;
            console.error('[UserConditions] API error response:', {
                status: response.status,
                statusText: response.statusText,
                error: errorMsg,
                response: result
            });
            throw new Error(errorMsg);
        }
        
        // If we get here, the request was successful (status 2xx)
        console.log(`[UserConditions] ${isEdit ? 'Update' : 'Create'} successful:`, {
            conditionId: result?.id || 'unknown',
            name: result?.name || 'unknown'
        });

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

// --- Guard all user-conditions modal/loader logic ---
(function() {
    // Only run if the user conditions modal or container exists
    const modalExists = document.getElementById('userConditionsModal');
    const containerExists = document.getElementById('user-conditions-list-container');
    if (!modalExists && !containerExists) {
        // Do not run any user-conditions logic on this page
        return;
    }
    
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
    
    // Handle form submission for saving user conditions
    const userConditionsForm = document.getElementById('user-conditions-form');
    if (userConditionsForm) {
        userConditionsForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Get all checked checkboxes
            const checkboxes = document.querySelectorAll('.condition-checkbox');
            const selectedConditions = [];
            
            checkboxes.forEach(checkbox => {
                const conditionId = checkbox.id.replace('condition-', '');
                if (checkbox.checked) {
                    selectedConditions.push(conditionId);
                }
            });
            
            try {
                const response = await fetch('/update-settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        conditions: selectedConditions,
                        condition_type: 'user' // To distinguish from admin conditions
                    })
                });
                
                if (response.ok) {
                    showToast('Conditions saved successfully', 'success');
                    // Close the modal after a short delay
                    setTimeout(() => {
                        const modal = bootstrap.Modal.getInstance(document.getElementById('userConditionsModal'));
                        if (modal) {
                            modal.hide();
                        }
                        // Refresh the dashboard to apply changes
                        if (typeof updateDashboard === 'function') {
                            updateDashboard();
                        }
                    }, 1000);
                } else {
                    throw new Error('Failed to save conditions');
                }
            } catch (error) {
                console.error('Error saving conditions:', error);
                showToast('Failed to save conditions', 'error');
            }
        });
    }
})();
