// dashboard/static/dashboard/js/app.js

let currentData = [];
let allCategoriesList = [];
let progressInterval = null;

// Initialize data from server (called inline from template)
function initDashboardData(categoriesJson) {
    allCategoriesList = categoriesJson;
    loadTab('ALL');
    
    // Start polling if banner is visible
    if(document.getElementById('jobBanner').style.display !== 'none') {
        const btn = document.getElementById('btnStartJob');
        if(btn && !btn.innerText.includes('All Products')) {
            btn.disabled = true;
            btn.innerText = 'Processing...';
        }
        progressInterval = setInterval(pollJobStatus, 2000);
    }
}

function uploadProducts(input) {
    if (!input.files || input.files.length === 0) return;
    
    const formData = new FormData();
    formData.append('file', input.files[0]);
    
    const btn = document.getElementById('btnUpload');
    btn.innerText = 'Uploading...';
    btn.disabled = true;

    fetch('/api/upload/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        alert(data.status || 'Upload started.');
        setTimeout(() => window.location.reload(), 3000);
    })
    .catch(err => {
        alert('Failed to upload.');
        btn.innerText = 'Upload Excel';
        btn.disabled = false;
    });
}

function startBatchJob() {
    const btn = document.getElementById('btnStartJob');
    btn.disabled = true;
    btn.innerText = 'Starting...';
    
    let batchSize = '10';
    const select = document.getElementById('batchSizeSelect');
    if (select) {
        batchSize = select.value;
        select.disabled = true;
    }

    fetch('/api/process-batch/', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken') 
        },
        body: JSON.stringify({ batch_size: batchSize })
    })
    .then(r => r.json())
    .then(data => {
        btn.innerText = 'Processing...';
        document.getElementById('jobBanner').style.display = 'block';
        if (!progressInterval) {
            progressInterval = setInterval(pollJobStatus, 2000);
        }
    })
    .catch(err => {
        alert('Failed to start job.');
        btn.disabled = false;
        btn.innerText = 'Start Batch Processor';
        const select = document.getElementById('batchSizeSelect');
        if (select) select.disabled = false;
    });
}

function pollJobStatus() {
    fetch(`/api/job-status/?t=${new Date().getTime()}`, { cache: 'no-store' })
    .then(r => r.json())
    .then(data => {
        // Update global stats
        if (data.stats) {
            const elTotal = document.getElementById('statTotal');
            if (elTotal) elTotal.innerText = data.stats.total;
            
            const elClass = document.getElementById('statClassified');
            if (elClass) elClass.innerText = data.stats.classified;
            
            const elPending = document.getElementById('statPending');
            if (elPending) elPending.innerText = data.stats.pending;
            
            const elReview = document.getElementById('statReview');
            if (elReview) elReview.innerText = data.stats.review;
            
            const elAvg = document.getElementById('statAvgConf');
            if (elAvg) elAvg.innerText = data.stats.avg_conf;
        }

        if (!data.id) return;
        
        document.getElementById('jobTitle').innerText = `Active Batch Job #${data.id}`;
        
        const badge = document.getElementById('jobStatusBadge');
        badge.innerText = data.status;
        badge.className = `badge ${data.status === 'COMPLETED' ? 'success' : (data.status === 'FAILED' ? 'danger' : 'warning')}`;
        
        let percent = 0;
        if(data.total_products > 0) {
            percent = Math.round((data.completed / data.total_products) * 100);
        }
        
        document.getElementById('jobProgressBar').style.width = `${percent}%`;
        document.getElementById('jobProgressText').innerText = `Completed: ${data.completed} / ${data.total_products} (Failed: ${data.failed})`;
        document.getElementById('jobProgressPercent').innerText = `${percent}%`;

        if (!data.active) {
            clearInterval(progressInterval);
            progressInterval = null;
            document.getElementById('btnStartJob').disabled = false;
            document.getElementById('btnStartJob').innerText = 'Start Batch Processor';
            
            // Reload table to show new results
            const activeTab = document.querySelector('.tab.active');
            loadTab(activeTab ? activeTab.innerText : 'ALL');
        }
    });
}

let currentPage = 1;
let currentTotalPages = 1;

function loadTab(tabName, page=1) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => {
        if(t.innerText.toUpperCase().includes(tabName.toUpperCase())) t.classList.add('active');
    });

    currentPage = page;
    let url = `/api/classifications/?page=${page}`;
    if(tabName === 'REVIEW') {
        url += '&manual_review=true';
    } else if(tabName === 'FAILED') {
        url += '&status=FAILED';
    }

    fetch(url)
    .then(r => r.json())
    .then(data => {
        currentData = data.results || data; // handle both paginated and unpaginated
        if(data.count !== undefined) {
            currentTotalPages = Math.ceil(data.count / 50);
        }
        renderTable(currentData);
        renderPagination();
    });
}

function renderPagination() {
    const indicator = document.getElementById('pageIndicator');
    if(indicator) {
        indicator.innerText = `Page ${currentPage} of ${currentTotalPages || 1}`;
        document.getElementById('btnPrevPage').disabled = (currentPage <= 1);
        document.getElementById('btnNextPage').disabled = (currentPage >= currentTotalPages);
    }
}

function changePage(delta) {
    const activeTab = document.querySelector('.tab.active');
    let tabName = 'ALL';
    if(activeTab) {
        if(activeTab.innerText.includes('Review')) tabName = 'REVIEW';
        else if(activeTab.innerText.includes('Failed')) tabName = 'FAILED';
    }
    loadTab(tabName, currentPage + delta);
}

function renderTable(data) {
    const tbody = document.getElementById('tableBody');
    tbody.innerHTML = '';
    
    data.forEach(item => {
        const tr = document.createElement('tr');
        
        // Status Badge
        let statusBadge = '';
        if(item.status === 'FAILED') statusBadge = `<span class="badge danger">Failed</span>`;
        else if(item.requires_manual_review) statusBadge = `<span class="badge warning">Needs Review</span>`;
        else statusBadge = `<span class="badge success">Approved</span>`;

        // Image
        const imgSrc = item.product_image || '';
        const imgHtml = imgSrc ? `<img src="${imgSrc}" class="thumbnail">` : `<div class="thumbnail"></div>`;

        tr.innerHTML = `
            <td>
                <div class="product-cell">
                    ${imgHtml}
                    <span>${item.product_name}</span>
                </div>
            </td>
            <td>${item.predicted_category || 'N/A'}</td>
            <td>${item.confidence ? parseFloat(item.confidence).toFixed(4) : '0'}</td>
            <td>${statusBadge}</td>
            <td><button class="btn" onclick="openModal(${item.id})">Inspect</button></td>
        `;
        tbody.appendChild(tr);
    });
}

function openModal(id) {
    const item = currentData.find(i => i.id === id);
    if(!item) return;

    document.getElementById('modalClassId').value = item.id;
    document.getElementById('modalTitle').innerText = item.product_name;
    
    const datalist = document.getElementById('categoryList');
    const input = document.getElementById('modalCategory');
    datalist.innerHTML = '';
    
    // Set current value
    const currentCat = allCategoriesList.find(c => c.id === item.predicted_category_id);
    input.value = currentCat ? currentCat.full_path : '';
    
    allCategoriesList.forEach(cat => {
        const option = document.createElement('option');
        option.value = cat.full_path;
        datalist.appendChild(option);
    });
    
    // Use AI extracted brand if DB brand is missing
    let displayBrand = item.product_brand;
    if (!displayBrand && item.attributes) {
        const extractedBrand = item.attributes.find(a => a.attribute_name.toLowerCase() === 'brand');
        if (extractedBrand) {
            displayBrand = extractedBrand.value + " (AI Extracted)";
        }
    }
    document.getElementById('modalBrand').innerText = displayBrand || 'Unknown';
    
    document.getElementById('modalDesc').innerText = item.product_description || 'No description available.';
    
    const img = document.getElementById('modalImg');
    if(item.product_image) {
        img.src = item.product_image;
        img.style.display = 'block';
    } else {
        img.style.display = 'none';
    }

    // Status Badge
    const statusDiv = document.getElementById('modalStatusBadge');
    if(item.status === 'FAILED') statusDiv.innerHTML = `<span class="badge danger">FAILED: ${item.failure_reason}</span>`;
    else if(item.requires_manual_review) statusDiv.innerHTML = `<span class="badge warning">Needs Manual Review</span>`;
    else statusDiv.innerHTML = `<span class="badge success">Approved</span>`;

    // Category Dropdown (AI Pick + Alternatives)
    const catSelect = document.getElementById('modalCategory');
    catSelect.innerHTML = '';
    if(item.predicted_category) {
        catSelect.innerHTML += `<option value="${item.predicted_category}" selected>${item.predicted_category} (AI Pick)</option>`;
    } else {
        catSelect.innerHTML += `<option value="" selected disabled>-- Select Category Manually --</option>`;
    }
    
    if(item.alternatives && item.alternatives.length > 0) {
        let optionsHtml = '';
        item.alternatives.forEach(alt => {
            optionsHtml += `<option value="${alt.category_name}">${alt.full_path} (Confidence: ${alt.confidence})</option>`;
        });
        catSelect.innerHTML += optionsHtml;
    } else {
        // Fallback: Populate with all categories from server if AI completely failed
        let optionsHtml = '';
        allCategoriesList.forEach(cat => {
            optionsHtml += `<option value="${cat.name}">${cat.full_path}</option>`;
        });
        catSelect.innerHTML += optionsHtml;
    }

    // Attributes
    const attrContainer = document.getElementById('modalAttributes');
    attrContainer.innerHTML = '';
    if(item.attributes && item.attributes.length > 0) {
        item.attributes.forEach(attr => {
            attrContainer.innerHTML += `
                <div style="margin-bottom: 12px;">
                    <div class="meta-label">${attr.attribute_name}</div>
                    <input type="text" value="${attr.value}" data-key="${attr.attribute_name}" class="attr-input">
                </div>
            `;
        });
    } else {
        attrContainer.innerHTML = '<p style="color:var(--text-secondary); font-size:0.875rem;">No attributes extracted.</p>';
    }

    document.getElementById('inspectModal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('inspectModal').style.display = 'none';
}

function saveClassification() {
    const id = document.getElementById('modalClassId').value;
    const newCategoryText = document.getElementById('modalCategory').value;
    
    const catObj = allCategoriesList.find(c => c.full_path === newCategoryText);
    const categoryId = catObj ? catObj.id : null;
    
    const attributes = {};
    document.querySelectorAll('.attr-input').forEach(input => {
        attributes[input.getAttribute('data-key')] = input.value;
    });
    
    // Disable button to prevent double submit
    const btn = event.target;
    btn.disabled = true;
    btn.innerText = 'Saving...';

    fetch(`/api/classifications/${id}/`, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            predicted_category: categoryId,
            requires_manual_review: false,
            status: 'approved',
            attributes: attributes
        })
    })
    .then(r => r.json())
    .then(data => {
        closeModal();
        btn.disabled = false;
        btn.innerText = 'Approve & Save';
        loadTab('ALL'); // Refresh table
    })
    .catch(err => {
        alert('Failed to save.');
        btn.disabled = false;
        btn.innerText = 'Approve & Save';
    });
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
