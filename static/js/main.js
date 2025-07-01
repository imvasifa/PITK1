// Import UserConditions module
import { UserConditions } from './modules/user-conditions.js';

// Initialize UserConditions
let userConditions = null;
document.addEventListener('DOMContentLoaded', () => {
    userConditions = new UserConditions();
});

// Functions to manage the Conditions Modal
async function populateAdminConditions() {
    const container = document.getElementById('admin-conditions-list');
    if (!container) return; // Exit if the element doesn't exist
    container.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';

    try {
        const [settingsRes, conditionsRes] = await Promise.all([
            fetch('/get-settings'),
            fetch('/conditions')
        ]);
        
        const settings = await settingsRes.json();
        const conditions = await conditionsRes.json();
        const selectedConditions = settings.conditions || [];

        container.innerHTML = '';
        // Always show all admin conditions
        const adminConditions = conditions.filter(c => c.type === 'admin');

        if (adminConditions.length === 0) {
            container.innerHTML = '<p>No admin conditions available.</p>';
            return;
        }

        adminConditions.forEach(condition => {
            const isChecked = selectedConditions.includes(condition.name);
            const conditionEl = document.createElement('label');
            conditionEl.className = 'list-group-item';
            conditionEl.innerHTML = `
                <input class="form-check-input me-1" type="checkbox" value="${condition.name}" ${isChecked ? 'checked' : ''}>
                ${condition.name}
            `;
            container.appendChild(conditionEl);
        });
    } catch (error) {
        console.error('Error populating admin conditions:', error);
        container.innerHTML = '<div class="alert alert-danger">Failed to load conditions.</div>';
    }
}

// Keep the populateUserConditions function for backward compatibility
async function populateUserConditions() {
    if (userConditions) {
        userConditions.loadConditions();
    } else {
        console.warn('UserConditions module not initialized yet');
        const container = document.getElementById('user-conditions-list-container');
        if (container) {
            container.innerHTML = '<div class="alert alert-warning">Loading user conditions...</div>';
        }
    }
}

// Ensure modal exists before adding event listener
const conditionsModal = document.getElementById('conditionsModal');
if (conditionsModal) {
    conditionsModal.addEventListener('show.bs.modal', function () {
        populateAdminConditions();
        populateUserConditions();
    });
}

// Ensure form exists before adding event listener
const updateSettingsForm = document.getElementById('update-settings-form');
if (updateSettingsForm) {
    updateSettingsForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const selected = Array.from(document.querySelectorAll('#admin-conditions-list input:checked')).map(el => el.value);
        
        try {
            const response = await fetch('/update-settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ conditions: selected })
            });
            const data = await response.json();
            if (data.success) {
                const modalInstance = bootstrap.Modal.getInstance(conditionsModal);
                if (modalInstance) {
                    modalInstance.hide();
                }
                window.location.reload(); // Reload to apply changes
            } else {
                alert('Failed to save settings.');
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            alert('An error occurred while saving settings.');
        }
    });
}

// Core dashboard functionality
function showLoading() {
    console.log("Showing loading overlay...");
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'flex';
    }
}

function hideLoading() {
    console.log("Hiding loading overlay...");
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

async function updateDashboard() {
    console.log("updateDashboard called. Showing loader.");
    showLoading();
    try {
        const response = await fetch('/get-scan-results');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        const container = document.getElementById('scan-results-container');
        if (!container) {
            console.error('Scan results container not found!');
            return;
        }
        
        container.innerHTML = ''; // Clear previous results

        if (Object.keys(data).length === 0) {
            container.innerHTML = '<div class="col-12"><div class="alert alert-info">No scan results found for the selected conditions.</div></div>';
            return;
        }

        for (const [condition, stocks] of Object.entries(data)) {
            const card = createCard(condition, stocks);
            container.appendChild(card);
        }
    } catch (error) {
        console.error('Error updating dashboard:', error);
        const container = document.getElementById('scan-results-container');
        if (container) {
            container.innerHTML = '<div class="col-12"><div class="alert alert-danger">Failed to load scan results. Please try refreshing the page.</div></div>';
        }
    } finally {
        console.log("updateDashboard finished. Hiding loader.");
        hideLoading();
    }
}

function createCard(condition, stocks) {
    const card = document.createElement('div');
    card.className = 'col-12 mb-4';

    let stockRows = '';
    if (stocks.length > 0) {
        stockRows = stocks.map(stock => `
            <tr>
                <td>${stock.symbol}</td>
                <td>${stock.close}</td>
                <td><a href="${stock.chartink_link}" target="_blank">View</a></td>
                <td class="${stock.per_chg >= 0 ? 'text-success' : 'text-danger'}">${stock.per_chg}%</td>
                <td>${stock.volume}</td>
                <td>${stock.score}</td>
            </tr>
        `).join('');
    } else {
        stockRows = '<tr><td colspan="6" class="text-center">No stocks found for this condition.</td></tr>';
    }

    card.innerHTML = `
        <div class="card scan-card">
            <div class="card-header">
                ${condition}
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover mb-0">
                        <thead>
                            <tr>
                                <th>Stock</th>
                                <th>Close</th>
                                <th>Chartink</th>
                                <th>Change %</th>
                                <th>Volume</th>
                                <th>Score</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${stockRows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    return card;
}

// Initial load
console.log("main.js loaded. Setting up DOMContentLoaded listener.");
document.addEventListener('DOMContentLoaded', function() {
    // Initial dashboard load
    updateDashboard();
    
    // Setup refresh button with cache-busting
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            console.log('Manual refresh triggered');
            // Add timestamp to bypass cache
            const timestamp = new Date().getTime();
            // Force reload the page with cache-busting
            window.location.href = window.location.pathname + '?t=' + timestamp;
        });
    }
});

// User Conditions Modal logic (restored)
const userConditionsModal = new bootstrap.Modal(document.getElementById('userConditionsModal'));
window.showCustomConditionsModal = function() {
    const modal = new bootstrap.Modal(document.getElementById('conditionsModal'));
    modal.show();
    // Switch to the 'Your Conditions' tab
    setTimeout(() => {
        const tab = document.getElementById('user-conditions-tab');
        if (tab) tab.click();
    }, 200);
};

// --- User Conditions Modal CRUD logic ---

// Show the add form
const showAddBtn = document.getElementById('show-add-condition-form-btn');
if (showAddBtn) {
    showAddBtn.onclick = function() {
        document.getElementById('user-condition-form-view').style.display = 'block';
        document.getElementById('user-conditions-list-view').style.display = 'none';
        document.getElementById('user-condition-form-title').textContent = 'Add New Condition';
        document.getElementById('user-condition-form').reset();
        document.getElementById('edit-condition-id').value = '';
    };
}

const cancelEditBtn = document.getElementById('cancel-edit-condition-btn');
if (cancelEditBtn) {
    cancelEditBtn.onclick = function() {
        document.getElementById('user-condition-form-view').style.display = 'none';
        document.getElementById('user-conditions-list-view').style.display = 'block';
    };
}

const userConditionForm = document.getElementById('user-condition-form');
if (userConditionForm) {
    userConditionForm.onsubmit = async function(e) {
        e.preventDefault();
        const id = document.getElementById('edit-condition-id').value;
        const name = document.getElementById('user-condition-name').value;
        const link = document.getElementById('user-condition-link').value;
        const clause = document.getElementById('user-condition-clause').value;
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/user-conditions/${id}` : '/api/user-conditions';
        const body = JSON.stringify({ name, link, scan_clause: clause });
        try {
            const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body
            });
            if (!response.ok) throw new Error('Failed to save condition');
            document.getElementById('user-condition-form-view').style.display = 'none';
            document.getElementById('user-conditions-list-view').style.display = 'block';
            loadUserConditions();
        } catch (err) {
            alert('Error saving condition: ' + err.message);
        }
    };
}

async function loadUserConditions() {
    const container = document.getElementById('user-conditions-list-container');
    if (!container) return;
    container.innerHTML = '<div class="text-center">Loading...</div>';
    try {
        const response = await fetch('/api/user-conditions');
        const conditions = await response.json();
        container.innerHTML = '';
        if (!conditions.length) {
            container.innerHTML = '<div class="text-muted text-center p-3">No custom conditions yet. Add one to get started!</div>';
            return;
        }
        conditions.forEach(condition => {
            const div = document.createElement('div');
            div.className = 'list-group-item d-flex justify-content-between align-items-center';
            div.innerHTML = `
                <div>
                    <h6 class="mb-1">${condition.name}</h6>
                    <small class="text-muted">${condition.scan_clause.substring(0, 100)}${condition.scan_clause.length > 100 ? '...' : ''}</small>
                </div>
                <div class="btn-group">
                    <button class="btn btn-sm btn-outline-primary" onclick='editUserCondition(${JSON.stringify(condition).replace(/"/g, "&quot;")})'>
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick='deleteUserCondition("${condition.id}")'>
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
            container.appendChild(div);
        });
    } catch (err) {
        container.innerHTML = '<div class="text-danger">Failed to load conditions.</div>';
    }
}

window.editUserCondition = function(condition) {
    document.getElementById('user-condition-form-view').style.display = 'block';
    document.getElementById('user-conditions-list-view').style.display = 'none';
    document.getElementById('user-condition-form-title').textContent = 'Edit Condition';
    document.getElementById('edit-condition-id').value = condition.id;
    document.getElementById('user-condition-name').value = condition.name;
    document.getElementById('user-condition-link').value = condition.link || '';
    document.getElementById('user-condition-clause').value = condition.scan_clause;
};

window.deleteUserCondition = async function(id) {
    const confirmed = await (typeof showConfirmDialog === 'function' ? showConfirmDialog('Are you sure you want to delete this condition?') : Promise.resolve(confirm('Are you sure you want to delete this condition?')));
    if (!confirmed) return;
    try {
        const response = await fetch(`/api/user-conditions/${id}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Failed to delete condition');
        loadUserConditions();
    } catch (err) {
        alert('Error deleting condition: ' + err.message);
    }
};

document.getElementById('userConditionsModal').addEventListener('shown.bs.modal', loadUserConditions);
// --- End User Conditions Modal CRUD logic ---

// Show Admin Conditions Modal
window.showConditionsModal = function() {
    const modal = new bootstrap.Modal(document.getElementById('conditionsModal'));
    modal.show();
};

// Initialize UserConditions when the tab is clicked
document.getElementById('user-conditions-tab').addEventListener('click', function() {
    if (window.userConditions) {
        window.userConditions.loadConditions();
    } else {
        console.warn('UserConditions module not initialized');
        populateUserConditions(); // Fallback to old method
    }
});

// Attach event listeners for user conditions form actions

function showAddConditionForm() {
    document.getElementById('user-conditions-list-view').style.display = 'none';
    document.getElementById('user-condition-form-view').style.display = 'block';
    document.getElementById('user-condition-form-title').textContent = 'Add New Condition';
    document.getElementById('edit-condition-id').value = '';
    document.getElementById('user-condition-form').reset();
}

function cancelEditCondition() {
    document.getElementById('user-conditions-list-view').style.display = 'block';
    document.getElementById('user-condition-form-view').style.display = 'none';
}

async function handleUserConditionSubmit(e) {
    e.preventDefault();
    const formData = {
        name: document.getElementById('user-condition-name').value,
        link: document.getElementById('user-condition-link').value || '#',
        scan_clause: document.getElementById('user-condition-clause').value
    };
    const editId = document.getElementById('edit-condition-id').value;
    const isEdit = editId !== '';
    try {
        const url = isEdit ? `/api/user-conditions/${editId}` : '/api/user-conditions';
        const method = isEdit ? 'PUT' : 'POST';
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        if (response.ok) {
            cancelEditCondition();
            populateUserConditions();
        } else {
            const data = await response.json();
            alert('Error saving condition: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error saving condition:', error);
        alert('Error saving condition.');
    }
}

document.getElementById('show-add-condition-form-btn').addEventListener('click', showAddConditionForm);
document.getElementById('cancel-edit-condition-btn').addEventListener('click', cancelEditCondition);
document.getElementById('user-condition-form').addEventListener('submit', handleUserConditionSubmit); 