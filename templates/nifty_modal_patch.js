// Nifty Modal Logic for dynamic table rendering
function showNiftyModal() {
    const modalBody = document.getElementById('niftyModalBody');
    const lastUpdated = document.getElementById('niftyLastUpdatedTime');
    if (!modalBody) return;
    // Show loader
    modalBody.innerHTML = `<div class="d-flex flex-column align-items-center justify-content-center" style="min-height:120px;">
        <div class="spinner-border text-info mb-2" role="status"><span class="visually-hidden">Loading...</span></div>
        <div class="loading-message">Fetching latest Nifty indices...</div>
    </div>`;
    if (lastUpdated) lastUpdated.textContent = '';
    fetch('/get_nifty_data')
        .then(response => response.json())
        .then(data => {
            if (!data || Object.keys(data).length === 0) {
                modalBody.innerHTML = '<div class="empty-state">No Nifty data available at this time.</div>';
                if (lastUpdated) lastUpdated.textContent = '';
                return;
            }
            // Build table
            let table = `<div class="table-responsive"><table class="table table-dark table-striped align-middle mb-0">
                <thead><tr>
                    <th>Index</th>
                    <th>Last</th>
                    <th>Open</th>
                    <th>Change</th>
                    <th>% Change</th>
                </tr></thead><tbody>`;
            for (const [index, values] of Object.entries(data)) {
                const change = parseFloat(values.change);
                const pChange = parseFloat(values.pChange);
                const changeClass = change < 0 ? 'text-danger fw-bold' : 'text-success fw-bold';
                const pChangeClass = pChange < 0 ? 'text-danger fw-bold' : 'text-success fw-bold';
                table += `<tr>
                    <td>${index}</td>
                    <td>${values.last}</td>
                    <td>${values.open}</td>
                    <td class="${changeClass}">${values.change}</td>
                    <td class="${pChangeClass}">${values.pChange}%</td>
                </tr>`;
            }
            table += '</tbody></table></div>';
            modalBody.innerHTML = table;
            // Set last updated time
            const now = new Date();
            if (lastUpdated) lastUpdated.textContent = `Last updated: ${now.toLocaleString()}`;
        })
        .catch(err => {
            modalBody.innerHTML = '<div class="empty-state">Failed to load Nifty data. Please try again later.</div>';
            if (lastUpdated) lastUpdated.textContent = '';
        });
}
// Attach to modal show event
const niftyModal = document.getElementById('niftyModal');
if (niftyModal) {
    niftyModal.addEventListener('show.bs.modal', showNiftyModal);
}
