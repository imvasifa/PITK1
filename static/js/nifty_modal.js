document.addEventListener('DOMContentLoaded', function() {
    // Get modal element
    const niftyModal = document.getElementById('niftyModal');
    if (!niftyModal) return;

    // Function to load Nifty data
    async function loadNiftyData() {
        const modalBody = document.getElementById('niftyModalBody');
        const lastUpdated = document.getElementById('niftyLastUpdatedTime');
        
        if (!modalBody) return;

        // Show loading state
        modalBody.innerHTML = `
            <div class="d-flex flex-column align-items-center justify-content-center" style="min-height:120px;">
                <div class="spinner-border text-info mb-2" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div>Fetching latest Nifty indices...</div>
            </div>`;

        try {
            // Fetch data
            const response = await fetch('/get_nifty_data');
            const data = await response.json();

            if (!data || Object.keys(data).length === 0) {
                throw new Error('No data available');
            }

            // Build table
            let table = `
                <div class="table-responsive">
                    <table class="table table-dark table-striped align-middle mb-0">
                        <thead>
                            <tr>
                                <th>Index</th>
                                <th>Last</th>
                                <th>Open</th>
                                <th>Change</th>
                                <th>% Change</th>
                            </tr>
                        </thead>
                        <tbody>`;

            // Add rows
            for (const [index, values] of Object.entries(data)) {
                const change = parseFloat(values.change);
                const pChange = parseFloat(values.pChange);
                const changeClass = change < 0 ? 'text-danger fw-bold' : 'text-success fw-bold';
                const pChangeClass = pChange < 0 ? 'text-danger fw-bold' : 'text-success fw-bold';
                
                table += `
                    <tr>
                        <td>${index}</td>
                        <td>${values.last}</td>
                        <td>${values.open}</td>
                        <td class="${changeClass}">${values.change}</td>
                        <td class="${pChangeClass}">${values.pChange}%</td>
                    </tr>`;
            }

            table += `</tbody></table></div>`;
            modalBody.innerHTML = table;

            // Update timestamp
            if (lastUpdated) {
                lastUpdated.textContent = `Last updated: ${new Date().toLocaleString()}`;
            }
        } catch (error) {
            console.error('Error loading Nifty data:', error);
            modalBody.innerHTML = `
                <div class="alert alert-danger">
                    Failed to load Nifty data. Please try again later.
                </div>`;
            if (lastUpdated) lastUpdated.textContent = '';
        }
    }

    // Load data when modal is shown
    niftyModal.addEventListener('show.bs.modal', loadNiftyData);

    // Handle reload button click
    const reloadBtn = document.getElementById('niftyReloadBtn');
    if (reloadBtn) {
        reloadBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            loadNiftyData();
        });
    }
});
