// static/js/cleaning.js

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Element References ---
    const tableContainer = document.getElementById('data-table-container');
    const loadingIndicator = document.getElementById('loading-indicator');
    const messageArea = document.getElementById('message-area');
    const errorArea = document.getElementById('error-area');
    const undoBtn = document.getElementById('undo-btn');
    const redoBtn = document.getElementById('redo-btn');
    const saveBtn = document.getElementById('save-btn');
    const saveFilenameInput = document.getElementById('save-filename');
    const savedFileInfo = document.getElementById('saved-file-info');
    const rowCountSpan = document.getElementById('row-count');
    const colCountSpan = document.getElementById('col-count');
    const sidebar = document.querySelector('.sidebar'); // Still need for sidebar tools
    const toastContainer = document.querySelector('.toast-container');
    const sourceInfoDisplay = document.getElementById('source-info-display');
    const autoCleanBtn = document.getElementById('auto-clean-btn');
    const optimizeCategoriesBtn = document.getElementById('optimize-categories-btn');

    const outlierColumnSelect = document.getElementById('outlier-column'); // Changed ID for clarity
    const outlierMethodSelect = document.getElementById('outlier-method-select');
    const outlierIqrControls = document.getElementById('outlier-iqr-controls');
    const outlierIqrFactorInput = document.getElementById('outlier-iqr-factor');
    const outlierZscoreControls = document.getElementById('outlier-zscore-controls');
    const outlierZscoreThresholdInput = document.getElementById('outlier-zscore-threshold');

    // --- References to Outlier Ranges Panel ---
    const showOutlierRangesBtn = document.getElementById('show-outlier-ranges-btn');
    const outlierRangesPanel = document.getElementById('outlier-ranges-panel');
    const outlierRangesLoading = document.getElementById('outlier-ranges-loading');
    const outlierRangesError = document.getElementById('outlier-ranges-error');
    const outlierRangesPlaceholder = document.getElementById('outlier-ranges-placeholder');
    const outlierRangesAccordion = document.getElementById('outlier-ranges-accordion');
    const outlierRangesPanelCloseBtn = document.getElementById('outlier-ranges-panel-close-btn');

    // --- References to Config Panel ---
    const toggleConfigPanelBtn = document.getElementById('config-panel-btn');
    const autoCleanConfigPanel = document.getElementById('auto-clean-config-panel');
    const configPanelCloseBtn = document.getElementById('config-panel-close-btn');
    const saveAutoCleanConfigBtn = document.getElementById('save-auto-clean-config-btn');
    const configMissingNumeric = document.getElementById('config-missing-numeric');
    const configMissingOther = document.getElementById('config-missing-other');
    const configCaseChange = document.getElementById('config-case-change');
    const configTrimWhitespace = document.getElementById('config-trim-whitespace');
    const configConvertNumeric = document.getElementById('config-convert-numeric');
    const configConvertDatetime = document.getElementById('config-convert-datetime');
    const configConvertCategory = document.getElementById('config-convert-category');
    // Config Form Elements
    const configOutlierHandling = document.getElementById('config-outlier-handling');
    const configOutlierFactorGroup = document.getElementById('outlier-factor-group');
    const configOutlierIqrFactor = document.getElementById('config-outlier-iqr-factor');
    const configOutlierZscoreGroup = document.getElementById('outlier-zscore-group');
    const configOutlierZscoreThreshold = document.getElementById('config-outlier-zscore-threshold');

    // --- References to Stats Panel ---
    const statsPanel = document.getElementById('stats-panel');
    const statsPanelContent = document.getElementById('stats-content'); // Main content area for general stats
    const statsPanelColumnName = document.getElementById('stats-panel-column-name');
    const statsPanelPlaceholder = document.getElementById('stats-panel-placeholder');
    const statsPanelLoading = document.getElementById('stats-panel-loading');
    const statsPanelError = document.getElementById('stats-panel-error');
    const statsPanelCloseBtn = document.getElementById('stats-panel-close-btn');
    // New elements for unique/duplicate sections
    const uniqueValuesSection = document.getElementById('unique-values-section');
    const uniqueValuesContainer = document.getElementById('unique-values-container');
    const uniqueValuesCountDisplay = document.getElementById('unique-values-count-display');
    const duplicateValuesSection = document.getElementById('duplicate-values-section');
    const duplicateValuesContainer = document.getElementById('duplicate-values-container');
    const duplicateValuesCountDisplay = document.getElementById('duplicate-values-count-display');


    // --- References to Modal Apply Buttons ---
    const applyFilterBtn = document.getElementById('apply-filter-btn');
    const applySortBtn = document.getElementById('apply-sort-btn');
    const applySplitBtn = document.getElementById('apply-split-btn');
    const applyCombineBtn = document.getElementById('apply-combine-btn');
    const applyRenameBtn = document.getElementById('apply-rename-btn');
    const applyDropBtn = document.getElementById('apply-drop-btn');

    // --- Modal Elements & Instances ---
    const filterModalEl = document.getElementById('filterModal');
    const sortModalEl = document.getElementById('sortModal');
    const splitModalEl = document.getElementById('splitModal');
    const combineModalEl = document.getElementById('combineModal');
    const renameModalEl = document.getElementById('renameModal');
    const dropModalEl = document.getElementById('dropModal');


    const filterModal = filterModalEl ? new bootstrap.Modal(filterModalEl) : null;
    const sortModal = sortModalEl ? new bootstrap.Modal(sortModalEl) : null;
    const splitModal = splitModalEl ? new bootstrap.Modal(splitModalEl) : null;
    const combineModal = combineModalEl ? new bootstrap.Modal(combineModalEl) : null;
    const renameModal = renameModalEl ? new bootstrap.Modal(renameModalEl) : null;
    const dropModal = dropModalEl ? new bootstrap.Modal(dropModalEl) : null;


    // ==================================================
    // --- Helper Functions ---
    // ==================================================

    function showLoading() {
        if (loadingIndicator) loadingIndicator.style.display = 'block';
        if (tableContainer) tableContainer.style.opacity = '0.5';
    }

    function hideLoading() {
        if (loadingIndicator) loadingIndicator.style.display = 'none';
        if (tableContainer) tableContainer.style.opacity = '1';
    }

    function getSelectedOptions(selectElement) {
        if (!selectElement) return [];
        return Array.from(selectElement.selectedOptions).map(option => option.value);
    }

    function displayToast(message, type = 'info') {
        const toastId = 'toast-' + Date.now();
        let bgColor = 'bg-primary';
        if (type === 'success') bgColor = 'bg-success';
        else if (type === 'error') bgColor = 'bg-danger';
        else if (type === 'warning') bgColor = 'bg-warning text-dark';

        const toastHTML = `
            <div id="${toastId}" class="toast align-items-center text-white ${bgColor} border-0" role="alert" aria-live="assertive" aria-atomic="true">
              <div class="d-flex"> <div class="toast-body"> ${message} </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
              </div> </div> `;
        if (toastContainer) {
            toastContainer.insertAdjacentHTML('beforeend', toastHTML);
            const toastElement = document.getElementById(toastId);
            if (toastElement) {
                const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
                toast.show();
                toastElement.addEventListener('hidden.bs.toast', () => { toastElement.remove(); });
            }
        } else { console.warn("Toast container not found. Message:", message); }
    }

    function handleError(errorData, status) {
        let errorMsg = 'An unknown error occurred.';
        if (errorData && errorData.error) { errorMsg = errorData.error; }
        else if (status) { errorMsg = `Request failed with status: ${status}`; }
        else if (errorData instanceof Error) { errorMsg = `Client-side error: ${errorData.message}`; }
        console.error('Error:', errorMsg, 'Status:', status, 'Data:', errorData);
        if (errorArea) errorArea.textContent = errorMsg;
        if (messageArea) messageArea.textContent = '';
        displayToast(errorMsg, 'error');
    }

    function updateTableAndStatus(data, modalToHide = null) {
        if (data.table_html && tableContainer) {
            // The table_html from render_table_html is a tuple: (html, total_rows, total_cols)
            // So, data.table_html[0] is the actual HTML string.
            if (Array.isArray(data.table_html) && data.table_html.length > 0) {
                tableContainer.innerHTML = data.table_html[0]; // Use the HTML part
            } else if (typeof data.table_html === 'string') {
                tableContainer.innerHTML = data.table_html; // Fallback if not a tuple
            }
        }
        if (data.total_rows !== undefined && rowCountSpan) {
            rowCountSpan.textContent = `Rows: ${data.total_rows}`;
        } else if (data.table_html && Array.isArray(data.table_html) && data.table_html.length > 1 && rowCountSpan) {
            rowCountSpan.textContent = `Rows: ${data.table_html[1]}`; // Use total_rows from tuple
        }

        if (data.total_columns !== undefined && colCountSpan) {
            colCountSpan.textContent = `Columns: ${data.total_columns}`;
            if (data.columns) { updateColumnSelectors(data.columns); }
        } else if (data.table_html && Array.isArray(data.table_html) && data.table_html.length > 2 && colCountSpan) {
            colCountSpan.textContent = `Columns: ${data.table_html[2]}`; // Use total_columns from tuple
            if (data.columns) { updateColumnSelectors(data.columns); } // Still update selectors if columns list provided
        } else if (data.columns && colCountSpan) { // Fallback if total_columns not directly in response
             colCountSpan.textContent = `Columns: ${data.columns.length}`;
             updateColumnSelectors(data.columns);
        }


        if (data.undo_redo_status) { updateUndoRedoButtons(data.undo_redo_status); }
        if (data.message) {
            // Check if df_modified is explicitly false (meaning no actual change)
            const dfNotModified = data.df_modified === false;
            if (!dfNotModified) { // Only show success toast if data was modified or no df_modified flag
                displayToast(data.message, 'success');
            }
            if (messageArea) messageArea.textContent = data.message;
            if (errorArea) errorArea.textContent = '';
            if (modalToHide && !data.error) { modalToHide.hide(); }
        }
        if (data.error) { handleError(data, null); }
        if (data.saved_filename) {
            if (saveFilenameInput) saveFilenameInput.value = data.saved_filename;
            if (savedFileInfo) {
                savedFileInfo.innerHTML = `<i class="bi bi-info-circle"></i> Current state saved as: ${data.saved_filename}`;
                savedFileInfo.classList.remove('text-muted');
                savedFileInfo.classList.add('text-info');
            }
        }
    }


    function updateColumnSelectors(columns) {
        const selects = document.querySelectorAll('select');
        selects.forEach(select => {
            if (select.id && (select.id.includes('-column') || select.id.includes('-cols') || select.id.includes('-name') || select.multiple)) {
                const currentValues = select.multiple ? getSelectedOptions(select) : [select.value];
                let placeholderOption = select.querySelector('option[value=""][disabled]');
                if (!placeholderOption) placeholderOption = select.querySelector('option[value=""]'); // Fallback if disabled not used
                const optionsHtml = columns.map(col => `<option value="${col}">${col}</option>`).join('');
                select.innerHTML = '';
                if (placeholderOption) select.appendChild(placeholderOption.cloneNode(true));
                select.insertAdjacentHTML('beforeend', optionsHtml);
                if (select.multiple) {
                    Array.from(select.options).forEach(option => { if (currentValues.includes(option.value)) { option.selected = true; } });
                } else if (columns.includes(currentValues[0])) {
                    select.value = currentValues[0];
                } else if (placeholderOption) {
                    select.value = placeholderOption.value;
                }
            }
        });
    }

    function updateUndoRedoButtons(status) {
        if (undoBtn) undoBtn.disabled = !status.undo_enabled;
        if (redoBtn) redoBtn.disabled = !status.redo_enabled;
    }

    // --- Parameter Gathering and Validation Helpers ---
    function getRequiredValue(elementId, paramName, isSelect = false, isMultiSelect = false, context = document) {
        const element = context.querySelector(`#${elementId}`);
        if (!element) { console.error(`Element ${elementId} not found.`); return { value: null, valid: false, msg: `Config error: ${elementId} missing.` }; }
        let value; let valid = true; let msg = '';
        if (isMultiSelect) {
            value = getSelectedOptions(element);
            if (!value || value.length === 0) { valid = false; msg = `Select at least one option for ${paramName}.`; }
        } else {
            value = element.value.trim();
            if (isSelect && !value) { valid = false; msg = `Select an option for ${paramName}.`; }
            if (element.required && !value && !isSelect && !element.value) { valid = false; msg = `Enter a value for ${paramName}.`; }
        }
        if (!valid) displayToast(msg, 'warning');
        return { value: valid ? value : null, valid: valid };
    }

    function getOptionalValue(elementId, paramName, defaultValue = null, context = document) {
        const element = context.querySelector(`#${elementId}`);
        return (element && element.value.trim()) ? element.value.trim() : defaultValue;
    }

    function getCheckboxValue(elementId, paramName, context = document) {
        const element = context.querySelector(`#${elementId}`);
        return element ? element.checked : false;
    }

    // --- Toggle Fill Value Input Helper ---
    function toggleFillValueInput() {
        const fillMissingMethodSelect = document.getElementById('fill-missing-method'); // Get within function scope
        const fillValueInputGroup = document.getElementById('fill-value-input-group');
        const fillValueInput = document.getElementById('fill-missing-value');
        if (fillMissingMethodSelect && fillValueInputGroup) {
            if (fillMissingMethodSelect.value === 'value') {
                fillValueInputGroup.style.display = ''; if (fillValueInput) fillValueInput.required = true;
            } else {
                fillValueInputGroup.style.display = 'none'; if (fillValueInput) { fillValueInput.required = false; fillValueInput.value = ''; }
            }
        }
    }




    // --- Helper: Toggle Right Panels (now handles three panels) ---
    function toggleRightPanel(panelToShow) {
        const panels = [statsPanel, autoCleanConfigPanel, outlierRangesPanel]; // Added outlierRangesPanel
        panels.forEach(panel => {
            if (panel) {
                if (panel === panelToShow && panel.style.display !== 'block') {
                    panel.style.display = 'block';
                } else if (panel !== panelToShow) {
                    panel.style.display = 'none';
                } else { // If panelToShow IS the panel and it's already block, toggle it off
                    panel.style.display = 'none';
                }
            }
        });
        // Unhighlight column header if all right panels are hidden
        if (panels.every(p => !p || p.style.display === 'none') && activeColumnHeader) {
            activeColumnHeader.classList.remove('active-stat-col');
            activeColumnHeader = null;
        }
    }


    // --- NEW: Functions for Outlier Ranges Panel ---
    async function fetchAndDisplayOutlierRanges() {
        if (!outlierRangesPanel || !outlierRangesAccordion || !outlierRangesLoading || !outlierRangesError || !outlierRangesPlaceholder) {
            console.error("Outlier ranges panel elements not found.");
            return;
        }

        toggleRightPanel(outlierRangesPanel); // Show this panel, hide others
        outlierRangesAccordion.innerHTML = ''; // Clear previous
        outlierRangesError.style.display = 'none';
        outlierRangesPlaceholder.style.display = 'none';
        outlierRangesLoading.style.display = 'block';

        try {
            const response = await fetch('/calculate_outlier_ranges');
            const data = await response.json();
            outlierRangesLoading.style.display = 'none';

            if (!response.ok) {
                throw new Error(data.error || `Failed to fetch ranges (Status: ${response.status})`);
            }

            if (data.ranges_data && Object.keys(data.ranges_data).length > 0) {
                populateOutlierRangesAccordion(data.ranges_data);
            } else if (data.message) { // Handle backend message like "no suitable columns"
                outlierRangesPlaceholder.textContent = data.message;
                outlierRangesPlaceholder.style.display = 'block';
            } else {
                outlierRangesPlaceholder.textContent = 'No numerical columns found or no ranges calculated.';
                outlierRangesPlaceholder.style.display = 'block';
            }

        } catch (error) {
            console.error("Error fetching outlier ranges:", error);
            outlierRangesLoading.style.display = 'none';
            outlierRangesError.textContent = `Error: ${error.message}`;
            outlierRangesError.style.display = 'block';
        }
    }

    function populateOutlierRangesAccordion(rangesData) {
        if (!outlierRangesAccordion) return;
        outlierRangesAccordion.innerHTML = ''; // Clear previous

        Object.entries(rangesData).forEach(([colName, colRangeInfo], index) => {
            const uniqueId = `range-${colName.replace(/[^a-zA-Z0-9]/g, "")}-${index}`; // Sanitize for ID
            let iqrHtml = '<h6>IQR Based Ranges:</h6><ul>';
            if (colRangeInfo.iqr && Object.keys(colRangeInfo.iqr).length > 0) {
                if (colRangeInfo.iqr.Error || colRangeInfo.iqr.Info) {
                    iqrHtml += `<li><em class="text-muted">${colRangeInfo.iqr.Error || colRangeInfo.iqr.Info}</em></li>`;
                } else {
                    for (const [factor, bounds] of Object.entries(colRangeInfo.iqr)) {
                        iqrHtml += `<li><strong>${factor}:</strong> <code>${bounds.lower}</code> to <code>${bounds.upper}</code></li>`;
                    }
                }
            } else {
                iqrHtml += '<li><em class="text-muted">Not applicable or error.</em></li>';
            }
            iqrHtml += '</ul>';

            let zscoreHtml = '<h6 class="mt-3">Z-score Based Ranges:</h6><ul>';
            if (colRangeInfo.zscore && Object.keys(colRangeInfo.zscore).length > 0) {
                if (colRangeInfo.zscore.Error || colRangeInfo.zscore.Info) {
                    zscoreHtml += `<li><em class="text-muted">${colRangeInfo.zscore.Error || colRangeInfo.zscore.Info}</em></li>`;
                } else {
                    for (const [threshold, bounds] of Object.entries(colRangeInfo.zscore)) {
                        zscoreHtml += `<li><strong>${threshold}:</strong> <code>${bounds.lower}</code> to <code>${bounds.upper}</code></li>`;
                    }
                }
            } else {
                zscoreHtml += '<li><em class="text-muted">Not applicable or error.</em></li>';
            }
            zscoreHtml += '</ul>';

            const accordionItem = `
                <div class="accordion-item">
                    <h2 class="accordion-header" id="heading-${uniqueId}">
                        <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse-${uniqueId}" aria-expanded="false" aria-controls="collapse-${uniqueId}">
                            <code>${colName}</code>
                        </button>
                    </h2>
                    <div id="collapse-${uniqueId}" class="accordion-collapse collapse" aria-labelledby="heading-${uniqueId}" data-bs-parent="#outlier-ranges-accordion">
                        <div class="accordion-body">
                            ${iqrHtml}
                            ${zscoreHtml}
                        </div>
                    </div>
                </div>
            `;
            outlierRangesAccordion.insertAdjacentHTML('beforeend', accordionItem);
        });
        if (Object.keys(rangesData).length === 0) {
            outlierRangesPlaceholder.textContent = 'No numerical columns found for outlier range calculation.';
            outlierRangesPlaceholder.style.display = 'block';
        }
    }


    // --- Helper: Get current config values from form ---
    function getAutoCleanConfigValues() {
        const config = {};
        if (configOutlierHandling) config.outlier_handling = configOutlierHandling.value;
        if (configOutlierIqrFactor) config.outlier_iqr_factor = parseFloat(configOutlierIqrFactor.value) || 1.5;
        if (configOutlierZscoreThreshold) config.outlier_zscore_threshold = parseFloat(configOutlierZscoreThreshold.value) || 3.0;

        const missingNumeric = document.getElementById('config-missing-numeric');
        if (missingNumeric) config.missing_numeric_method = missingNumeric.value;
        const missingOther = document.getElementById('config-missing-other');
        if (missingOther) config.missing_other_method = missingOther.value;

        const caseChange = document.getElementById('config-case-change');
        if (caseChange) config.case_change_method = caseChange.value;

        const trimWhitespace = document.getElementById('config-trim-whitespace');
        if (trimWhitespace) config.trim_whitespace = trimWhitespace.checked;
        const convertNumeric = document.getElementById('config-convert-numeric');
        if (convertNumeric) config.convert_numeric = convertNumeric.checked;
        const convertDatetime = document.getElementById('config-convert-datetime');
        if (convertDatetime) config.convert_datetime = convertDatetime.checked;
        const convertCategory = document.getElementById('config-convert-category');
        if (convertCategory) config.convert_category = convertCategory.checked;

        return config;
    }

    // --- Helper: Populate config form from session/defaults (call on page load) ---
    async function loadAutoCleanConfigToForm() {
        try {
            const response = await fetch('/get_auto_clean_config'); // Fetch config from backend
            if (!response.ok) {
                console.error('Failed to fetch auto-clean config:', response.status);
                // Fallback to setting default visibility if fetch fails
                if (configOutlierHandling) toggleOutlierParameterVisibility();
                return;
            }
            const data = await response.json();
            const savedConfig = data.config;

            if (savedConfig) {
                if (configOutlierHandling) configOutlierHandling.value = savedConfig.outlier_handling || 'none';
                if (configOutlierIqrFactor) configOutlierIqrFactor.value = savedConfig.outlier_iqr_factor || 1.5;
                if (configOutlierZscoreThreshold) configOutlierZscoreThreshold.value = savedConfig.outlier_zscore_threshold || 3.0;

                if (configMissingNumeric) configMissingNumeric.value = savedConfig.missing_numeric_method || 'median';
                if (configMissingOther) configMissingOther.value = savedConfig.missing_other_method || 'ffill_bfill';

                if (configCaseChange) configCaseChange.value = savedConfig.case_change_method || 'none';

                if (configTrimWhitespace) configTrimWhitespace.checked = savedConfig.hasOwnProperty('trim_whitespace') ? savedConfig.trim_whitespace : true;
                if (configConvertNumeric) configConvertNumeric.checked = savedConfig.hasOwnProperty('convert_numeric') ? savedConfig.convert_numeric : true;
                if (configConvertDatetime) configConvertDatetime.checked = savedConfig.hasOwnProperty('convert_datetime') ? savedConfig.convert_datetime : true;
                if (configConvertCategory) configConvertCategory.checked = savedConfig.hasOwnProperty('convert_category') ? savedConfig.convert_category : true;
            }
        } catch (error) {
            console.error("Error loading auto-clean config:", error);
            // Don't show a toast here, as it's part of page load, just log.
            // displayToast("Could not load auto-clean config from server.", "warning");
        } finally {
            // Always update visibility of outlier params after attempting to load/set values
            if (configOutlierHandling) toggleOutlierParameterVisibility();
        }
    }


    // --- Helper: Toggle Outlier Factor Input Visibility ---
    function toggleOutlierParameterVisibility() {
        if (configOutlierHandling && configOutlierFactorGroup && configOutlierZscoreGroup) {
            const selectedMethod = configOutlierHandling.value;
            if (selectedMethod === 'clip_iqr' || selectedMethod === 'remove_iqr') {
                configOutlierFactorGroup.style.display = 'block';
                configOutlierZscoreGroup.style.display = 'none';
            } else if (selectedMethod === 'clip_zscore' || selectedMethod === 'remove_zscore') {
                configOutlierFactorGroup.style.display = 'none';
                configOutlierZscoreGroup.style.display = 'block';
            } else { // 'none' or other
                configOutlierFactorGroup.style.display = 'none';
                configOutlierZscoreGroup.style.display = 'none';
            }
        }
    }


    // ==================================================
    // --- Column Statistics Functions ---
    // ==================================================
    let activeColumnHeader = null; // Keep track of the highlighted header

    async function fetchAndDisplayColumnStats(columnName) {
        if (!statsPanel || !statsPanelContent || !statsPanelColumnName || !statsPanelLoading || !statsPanelError || !statsPanelPlaceholder) {
            console.error("Stats panel elements not found.");
            return;
        }

        // Show panel and loading state
        statsPanel.style.display = 'block';
        statsPanelColumnName.textContent = `Stats: ${columnName}`;
        statsPanelPlaceholder.style.display = 'none';
        statsPanelError.style.display = 'none';
        statsPanelContent.innerHTML = ''; // Clear previous stats
        statsPanelLoading.style.display = 'block';

        // Hide unique/duplicate sections until data is ready
        if (uniqueValuesSection) uniqueValuesSection.style.display = 'none';
        if (duplicateValuesSection) duplicateValuesSection.style.display = 'none';


        try {
            const response = await fetch(`/column_stats/${encodeURIComponent(columnName)}`);
            const data = await response.json();

            statsPanelLoading.style.display = 'none'; // Hide loading

            if (!response.ok) {
                throw new Error(data.error || `Failed to fetch stats (Status: ${response.status})`);
            }

            if (data.stats) {
                updateStatsPanel(columnName, data, data.dtype); // Pass full data object
            } else {
                statsPanelError.textContent = 'No statistics data received.';
                statsPanelError.style.display = 'block';
            }

        } catch (error) {
            console.error("Error fetching column stats:", error);
            statsPanelLoading.style.display = 'none';
            statsPanelError.textContent = `Error: ${error.message}`;
            statsPanelError.style.display = 'block';
        }
    }

    function updateStatsPanel(columnName, statsData, dtype) {
        // statsData here is the full response object from /column_stats, which includes .stats, .dtype etc.
        const stats = statsData.stats; // The actual statistics object

        if (!statsPanelContent || !statsPanelColumnName || !statsPanelPlaceholder ||
            !uniqueValuesSection || !uniqueValuesContainer || !uniqueValuesCountDisplay ||
            !duplicateValuesSection || !duplicateValuesContainer || !duplicateValuesCountDisplay) {
            console.error("One or more stats panel elements are missing.");
            return;
        }

        statsPanelColumnName.textContent = `Stats: ${columnName}`;
        statsPanelPlaceholder.style.display = 'none';
        statsPanelContent.innerHTML = ''; // Clear previous general stats container
        uniqueValuesSection.style.display = 'none';
        duplicateValuesSection.style.display = 'none';

        // Populate General Statistics
        const generalStatsUl = document.createElement('ul');
        let generalStatsAdded = false;
        const overviewKeys = [
            'Data Type', 'Total Rows (DataFrame)', 'Non-Missing Values', 'Missing Values', 'Missing (%)',
            'Unique Values (Incl. NaN)', 'Unique (%) (Incl. NaN)', 'Memory Usage',
            'Mean', 'Std Dev', 'Min', '25% (Q1)', 'Median (50%)', '75% (Q3)', 'Max',
            'Zero Count', 'Negative Count', 'Outliers (IQR, 1.5x)', 'Outliers (%)',
            'First Date', 'Last Date',
            'Most Frequent Value', 'Frequency (Most Freq.)',
            'Min Length', 'Max Length', 'Avg Length'
            // 'Value Counts (Boolean)' and other more complex objects handled separately if needed or by simple stringify
        ];

        overviewKeys.forEach(key => {
            if (stats.hasOwnProperty(key)) {
                const li = document.createElement('li');
                const labelSpan = document.createElement('span');
                labelSpan.className = 'stat-label';
                labelSpan.textContent = key + ':';
                const valueSpan = document.createElement('span');
                valueSpan.className = 'stat-value';

                let value = stats[key];
                if (typeof value === 'object' && value !== null && key.toLowerCase().includes('value counts')) {
                    // Prettier display for boolean value counts
                    value = Object.entries(value).map(([k, v]) => `${k}: ${v}`).join(', ');
                } else {
                    value = (value === null || value === undefined || String(value).toLowerCase() === 'nan' || String(value) === '<na>') ? 'NULL' : value;
                }
                valueSpan.textContent = String(value); // Ensure it's a string

                li.appendChild(labelSpan);
                li.appendChild(valueSpan);
                generalStatsUl.appendChild(li);
                generalStatsAdded = true;
            }
        });

        if (generalStatsAdded) {
            const overviewHeader = document.createElement('h6');
            overviewHeader.textContent = "Summary Statistics";
            statsPanelContent.appendChild(overviewHeader);
            statsPanelContent.appendChild(generalStatsUl);
        }


        // --- Populate Unique Values ---
        uniqueValuesContainer.innerHTML = '<p class="placeholder-text">Loading unique values...</p>';
        uniqueValuesCountDisplay.textContent = '';

        const uniqueSample = stats['unique_values_sample'];
        const totalUniqueCount = stats['unique_values_total_count'];

        if (uniqueSample && Array.isArray(uniqueSample)) {
            uniqueValuesSection.style.display = 'block';
            if (uniqueSample.length > 0) {
                const ul = document.createElement('ul');
                uniqueSample.forEach(value => {
                    const li = document.createElement('li');
                    const valueSpan = document.createElement('span');
                    valueSpan.className = 'value-item';
                    valueSpan.textContent = (String(value).toLowerCase() === 'nan' || String(value) === '<na>') ? 'NULL' : String(value);
                    li.appendChild(valueSpan);
                    ul.appendChild(li);
                });
                uniqueValuesContainer.innerHTML = '';
                uniqueValuesContainer.appendChild(ul);

                let countText = `Showing ${uniqueSample.length}`;
                if (totalUniqueCount !== undefined) {
                    countText += ` of ${totalUniqueCount} total unique value(s).`;
                }
                uniqueValuesCountDisplay.textContent = countText;

                if (totalUniqueCount > uniqueSample.length) {
                    const p = document.createElement('p');
                    p.className = 'text-muted small mt-1 fst-italic';
                    p.textContent = `...and ${totalUniqueCount - uniqueSample.length} more.`;
                    uniqueValuesContainer.appendChild(p);
                }
            } else {
                uniqueValuesContainer.innerHTML = '<p class="placeholder-text">No unique values found (or column is empty/all same).</p>';
                if (totalUniqueCount !== undefined) {
                    uniqueValuesCountDisplay.textContent = `Total unique values: ${totalUniqueCount}.`;
                }
            }
        } else {
            uniqueValuesContainer.innerHTML = '<p class="placeholder-text">Unique value data not available.</p>';
        }


        // --- Populate Duplicate Values ---
        duplicateValuesContainer.innerHTML = '<p class="placeholder-text">Loading duplicate values...</p>';
        duplicateValuesCountDisplay.textContent = '';

        const duplicatesSample = stats['duplicate_values_sample'];
        const totalDistinctDuplicates = stats['duplicate_values_distinct_count'];

        if (duplicatesSample && Array.isArray(duplicatesSample)) {
            duplicateValuesSection.style.display = 'block';
            if (duplicatesSample.length > 0) {
                const ul = document.createElement('ul');
                duplicatesSample.forEach(pair => {
                    const value = pair[0];
                    const count = pair[1];
                    const li = document.createElement('li');

                    const valueSpan = document.createElement('span');
                    valueSpan.className = 'value-item';
                    valueSpan.textContent = (String(value).toLowerCase() === 'nan' || String(value) === '<na>') ? 'NULL' : String(value);

                    const countSpan = document.createElement('span');
                    countSpan.className = 'count-item';
                    countSpan.textContent = `${count}`;

                    li.appendChild(valueSpan);
                    li.appendChild(countSpan);
                    ul.appendChild(li);
                });
                duplicateValuesContainer.innerHTML = '';
                duplicateValuesContainer.appendChild(ul);

                let countText = `Showing ${duplicatesSample.length}`;
                if (totalDistinctDuplicates !== undefined) {
                    countText += ` of ${totalDistinctDuplicates} distinct duplicated value(s).`;
                }
                duplicateValuesCountDisplay.textContent = countText;

                if (totalDistinctDuplicates > duplicatesSample.length) {
                    const p = document.createElement('p');
                    p.className = 'text-muted small mt-1 fst-italic';
                    p.textContent = `...and ${totalDistinctDuplicates - duplicatesSample.length} more distinct duplicated values.`;
                    duplicateValuesContainer.appendChild(p);
                }
            } else {
                duplicateValuesContainer.innerHTML = '<p class="placeholder-text">No duplicate values found (all values are unique or appear once).</p>';
                if (totalDistinctDuplicates !== undefined) {
                    duplicateValuesCountDisplay.textContent = `Total distinct duplicated values: ${totalDistinctDuplicates}.`;
                }
            }
        } else {
            duplicateValuesContainer.innerHTML = '<p class="placeholder-text">Duplicate value data not available.</p>';
        }

        statsPanel.style.display = 'block'; // Ensure panel is visible
        statsPanelLoading.style.display = 'none';
        statsPanelError.style.display = 'none';
    }


    function handleColumnHeaderClick(event) {
        const th = event.target.closest('th');
        if (th && th.parentElement.parentElement.tagName === 'THEAD' && tableContainer.contains(th)) {
            const columnName = th.textContent.trim();
            if (columnName) {
                if (activeColumnHeader) {
                    activeColumnHeader.classList.remove('active-stat-col');
                }
                th.classList.add('active-stat-col');
                activeColumnHeader = th;

                fetchAndDisplayColumnStats(columnName);
                toggleRightPanel(statsPanel); // This will show statsPanel and hide others
            }
        }
    }



    // ==================================================
    // --- Main Action Function ---
    // ==================================================

    async function performAction(url, method = 'POST', body = null, modalInstance = null) {
        showLoading();
        if (messageArea) messageArea.textContent = '';
        if (errorArea) errorArea.textContent = '';
        let responseData = {};

        try {
            const fetchOptions = { method: method, headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', }, body: body ? JSON.stringify(body) : null };
            const response = await fetch(url, fetchOptions);
            try { responseData = await response.json(); }
            catch (e) { if (!response.ok) throw { errorData: { error: `Status ${response.status} with non-JSON response.` }, status: response.status }; }
            if (!response.ok) { throw { errorData: responseData, status: response.status }; }

            updateTableAndStatus(responseData, modalInstance); // Pass modal instance

        } catch (errorInfo) {
            handleError(errorInfo.errorData || errorInfo, errorInfo.status);
        } finally {
            hideLoading();
        }
    } // End performAction


    // ==================================================
    // --- Event Listener Setup ---
    // ==================================================


    // NEW: Listener for Outlier Method Select
    if (outlierMethodSelect) {
        outlierMethodSelect.addEventListener('change', toggleOutlierMethodControls);
    }

    // --- NEW: Listener for Show Outlier Ranges Button ---
    if (showOutlierRangesBtn) {
        showOutlierRangesBtn.addEventListener('click', fetchAndDisplayOutlierRanges);
    }
    if (outlierRangesPanelCloseBtn) {
        outlierRangesPanelCloseBtn.addEventListener('click', () => {
            toggleRightPanel(null); // Hide all right panels
        });
    }


    // --- Listener for Column Header Clicks (for Stats Panel) ---
    // This listener is ALREADY set up correctly. No change needed here.

    // --- Listener for Stats Panel Close Button ---
    if (statsPanelCloseBtn) {
        statsPanelCloseBtn.addEventListener('click', () => {
            toggleRightPanel(null); // Hide all right panels
        });
    }


    // --- Listeners for Config Panel ---
    if (toggleConfigPanelBtn) {
        toggleConfigPanelBtn.addEventListener('click', () => {
            toggleRightPanel(autoCleanConfigPanel);
            // If statsPanel was open, explicitly hide it (toggleRightPanel handles this now)
        });
    }
    if (configPanelCloseBtn) {
        configPanelCloseBtn.addEventListener('click', () => {
            toggleRightPanel(null);
        });
    }
    if (configOutlierHandling) {
        configOutlierHandling.addEventListener('change', toggleOutlierParameterVisibility);
    }


    // NEW: Listener for Saving Auto Clean Config
    if (saveAutoCleanConfigBtn) {
        saveAutoCleanConfigBtn.addEventListener('click', async () => {
            const currentConfig = getAutoCleanConfigValues();
            showLoading();
            try {
                const response = await fetch('/save_auto_clean_config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(currentConfig)
                });
                const data = await response.json();
                if (response.ok) {
                    displayToast(data.message || 'Configuration saved successfully!', 'success');
                    console.log("Saved config:", data.config); // For debugging
                } else {
                    handleError(data, response.status);
                }
            } catch (error) {
                handleError(error, null);
            } finally {
                hideLoading();
            }
        });
    }


    // --- Listener for Column Header Clicks (Event Delegation) ---
    if (tableContainer) {
        tableContainer.addEventListener('click', handleColumnHeaderClick);
    }

    // --- Listener for Stats Panel Close Button ---
    // This listener is ALREADY set up correctly.

    if (autoCleanBtn) {
        autoCleanBtn.addEventListener('click', () => {
            if (confirm("Apply Auto Clean with current configuration? (Can be undone)")) {
                performAction('/auto_clean', 'POST');
            }
        });
    }


    // --- Helper: Toggle Outlier Controls Visibility ---
    function toggleOutlierMethodControls() {
        if (outlierMethodSelect && outlierIqrControls && outlierZscoreControls) {
            const selectedMethod = outlierMethodSelect.value;
            if (selectedMethod === 'iqr') {
                outlierIqrControls.style.display = 'flex'; // Or 'block' depending on input-group
                outlierZscoreControls.style.display = 'none';
            } else if (selectedMethod === 'zscore') {
                outlierIqrControls.style.display = 'none';
                outlierZscoreControls.style.display = 'flex'; // Or 'block'
            } else {
                outlierIqrControls.style.display = 'none';
                outlierZscoreControls.style.display = 'none';
            }
        }
    }


    // --- Event Listener for SIDEBAR actions ---
    function handleSidebarClick(event) {
        const button = event.target.closest('button[data-action]');
        if (!button) return;

        const action = button.dataset.action;
        const sidebarActions = [
            'remove_duplicates', 'remove_missing', 'fill_missing', 'remove_spaces',
            'change_dtype', 'fix_datetime', 'check_id_uniqueness', 'check_id_format',
            'remove_outliers_iqr', 'clip_outliers_iqr',
            'remove_outliers_zscore', 'clip_outliers_zscore',
            'replace_text', 'change_case', 'map_values'
        ];

        if (!sidebarActions.includes(action)) return;

        let params = {};
        let body = { operation: action, params: params };
        let validationOk = true;
        const controlGroup = button.closest('.cleaning-control') || sidebar;

        try {
            if (action === 'remove_duplicates') { /* No params */ }
            else if (action === 'remove_missing') { params.how = button.dataset.params ? JSON.parse(button.dataset.params).how : 'any'; }
            else if (action === 'fill_missing') {
                params.method = controlGroup.querySelector('#fill-missing-method')?.value || 'value';
                const colSelect = controlGroup.querySelector('#fill-missing-column');
                params.column = colSelect ? (colSelect.value || null) : null;
                if (params.column === "") params.column = null;
                if (params.method === 'value') {
                    const valResult = getRequiredValue('fill-missing-value', 'Value', false, false, controlGroup);
                    if (!valResult.valid) validationOk = false; else params.value = valResult.value;
                }
            }
            else if (action === 'remove_spaces') {
                const colRes = getRequiredValue('remove-spaces-column', 'Column', true, false, controlGroup);
                if (!colRes.valid) validationOk = false; else params.column = colRes.value;
            }
            else if (action === 'change_dtype') {
                const colRes = getRequiredValue('change-dtype-column', 'Column', true, false, controlGroup);
                const typeRes = getRequiredValue('change-dtype-target-type', 'Target Type', true, false, controlGroup);
                if (!colRes.valid || !typeRes.valid) validationOk = false;
                else { params.column = colRes.value; params.target_type = typeRes.value; }
            }
            else if (action === 'fix_datetime') {
                const colRes = getRequiredValue('fix-datetime-column', 'Column', true, false, controlGroup);
                if (!colRes.valid) validationOk = false; else params.column = colRes.value;
                params.format = getOptionalValue('fix-datetime-format', 'format', null, controlGroup);
            }
            else if (action === 'check_id_uniqueness') {
                const colRes = getRequiredValue('check-id-uniqueness-column', 'Column', true, false, controlGroup);
                if (!colRes.valid) validationOk = false; else params.column = colRes.value;
            }
            else if (action === 'check_id_format') {
                const colRes = getRequiredValue('check-id-format-column', 'Column', true, false, controlGroup);
                const patternRes = getRequiredValue('check-id-format-pattern', 'Pattern', false, false, controlGroup);
                if (!colRes.valid || !patternRes.valid) validationOk = false;
                else { params.column = colRes.value; params.pattern = patternRes.value; }
            }
            else if (action.includes('outliers_iqr') || action.includes('outliers_zscore')) {
                const colResult = getRequiredValue('outlier-column', 'Column', true, false, controlGroup);
                if (!colResult.valid) { validationOk = false; }
                else {
                    params.column = colResult.value;
                    if (action.includes('iqr')) {
                        const factorResult = getRequiredValue('outlier-iqr-factor', 'IQR Factor', false, false, document.getElementById('outlier-iqr-controls'));
                        if (!factorResult.valid) validationOk = false; else params.factor = parseFloat(factorResult.value);
                    } else if (action.includes('zscore')) {
                        const thresholdResult = getRequiredValue('outlier-zscore-threshold', 'Z-score Threshold', false, false, document.getElementById('outlier-zscore-controls'));
                        if (!thresholdResult.valid) validationOk = false; else params.threshold = parseFloat(thresholdResult.value);
                    }
                }
            }
            else if (action === 'replace_text') {
                const colRes = getRequiredValue('replace-text-column', 'Column', true, false, controlGroup);
                if (!colRes.valid) validationOk = false; else params.column = colRes.value;
                const findInputEl = controlGroup.querySelector('#replace-text-find');
                if (findInputEl) { params.text_to_find = findInputEl.value; }
                else { displayToast("Find text input not found.", "error"); validationOk = false; }
                params.replace_with = getOptionalValue('replace-text-replace', 'replace_with', '', controlGroup);
                params.use_regex = getCheckboxValue('replace-text-regex', 'use_regex', controlGroup);
            }
            else if (action === 'change_case') {
                const colRes = getRequiredValue('change-case-column', 'Column', true, false, controlGroup);
                const typeRes = getRequiredValue('change-case-type', 'Case Type', true, false, controlGroup);
                if (!colRes.valid || !typeRes.valid) validationOk = false;
                else { params.column = colRes.value; params.case_type = typeRes.value; }
            }
            else if (action === 'map_values') {
                const colRes = getRequiredValue('map-values-column', 'Column', true, false, controlGroup);
                const mapStrRes = getRequiredValue('map-values-dict', 'Mapping Dictionary', false, false, controlGroup);
                if (!colRes.valid || !mapStrRes.valid) validationOk = false;
                else {
                    params.column = colRes.value;
                    try { params.mapping_dict = JSON.parse(mapStrRes.value); }
                    catch (e) { displayToast(`Invalid JSON for mapping: ${e.message}`, 'error'); validationOk = false; }
                }
            }
        } catch (e) {
            console.error("Error gathering parameters from sidebar:", e);
            displayToast("Client-side error getting parameters from sidebar.", "error");
            validationOk = false;
        }

        if (validationOk) {
            performAction('/clean_operation', 'POST', body);
        }
    }




    // --- Event Listeners for MODAL Apply Buttons ---
    function addModalApplyListener(button, modalInstance, modalElement, action, paramGetterFn) {
        if (!modalElement) { console.warn(`Modal element not provided for action "${action}".`); return; }
        if (button && modalInstance) {
            button.addEventListener('click', () => {
                const { params, valid } = paramGetterFn(modalElement);
                if (valid) {
                    const body = { operation: action, params: params };
                    performAction('/clean_operation', 'POST', body, modalInstance);
                }
            });
        } else {
            if (!button) console.warn(`Button for modal action "${action}" not found.`);
        }
    }

    // --- Parameter Getters for Modals ---
    function getFilterParams(modalEl) {
        let params = {}; let valid = true;
        const colRes = getRequiredValue('modal-filter-column', 'Column', true, false, modalEl);
        const condRes = getRequiredValue('modal-filter-condition', 'Condition', true, false, modalEl);
        if (!colRes.valid || !condRes.valid) { valid = false; }
        else {
            params.column = colRes.value; params.condition = condRes.value;
            params.action = getOptionalValue('modal-filter-action', 'action', 'keep', modalEl);
            if (!['isnull', 'notnull'].includes(params.condition)) {
                const valRes = getRequiredValue('modal-filter-value', 'Value', false, false, modalEl);
                if (!valRes.valid && modalEl.querySelector('#modal-filter-value').value !== '') { valid = false; }
                else if (valRes.valid || modalEl.querySelector('#modal-filter-value').value === '') {
                    params.value = modalEl.querySelector('#modal-filter-value').value;
                } else { valid = false; }
            } else {
                params.value = null;
                const enteredValue = getOptionalValue('modal-filter-value', 'value', null, modalEl);
                if (enteredValue !== null && enteredValue !== '') { displayToast("Value entered but condition is 'Is Null' or 'Is Not Null'. Value will be ignored.", 'info'); }
            }
        } return { params, valid };
    }
    function getSortParams(modalEl) {
        let params = {}; let valid = true;
        const colsRes = getRequiredValue('modal-sort-cols', 'Columns', false, true, modalEl);
        if (!colsRes.valid) { valid = false; }
        else {
            params.columns_to_sort_by = colsRes.value;
            params.ascending = (getOptionalValue('modal-sort-ascending', 'ascending', 'true', modalEl) === 'true');
        }
        return { params, valid };
    }

    function getSplitParams(modalEl) {
        let params = {}; let valid = true;
        const colRes = getRequiredValue('modal-split-column', 'Column', true, false, modalEl);
        const delimRes = getRequiredValue('modal-split-delimiter', 'Delimiter', false, false, modalEl);
        if (!colRes.valid || !delimRes.valid) { valid = false; }
        else {
            params.column = colRes.value; params.delimiter = delimRes.value;
            params.new_column_names = getOptionalValue('modal-split-new-names', 'new_column_names', null, modalEl);
        }
        return { params, valid };
    }
    function getCombineParams(modalEl) {
        let params = {}; let valid = true;
        const colsRes = getRequiredValue('modal-combine-cols', 'Columns', false, true, modalEl);
        const nameRes = getRequiredValue('modal-combine-new-name', 'New Name', false, false, modalEl);
        if (!colsRes.valid || !nameRes.valid) { valid = false; }
        else if (colsRes.value.length < 2) { displayToast('Please select at least two columns to combine.', 'warning'); valid = false; }
        else {
            params.columns_to_combine = colsRes.value;
            params.new_column_name = nameRes.value;
            params.separator = getOptionalValue('modal-combine-separator', 'separator', '', modalEl);
        }
        return { params, valid };
    }

    function getRenameParams(modalEl) {
        let params = {}; let valid = true;
        const oldNameRes = getRequiredValue('modal-rename-old-name', 'Column', true, false, modalEl);
        const newNameRes = getRequiredValue('modal-rename-new-name', 'New Name', false, false, modalEl);
        if (!oldNameRes.valid || !newNameRes.valid) { valid = false; }
        else { params.old_name = oldNameRes.value; params.new_name = newNameRes.value; }
        return { params, valid };
    }

    function getDropParams(modalEl) {
        let params = {}; let valid = true;
        const colsRes = getRequiredValue('modal-drop-cols', 'Columns', false, true, modalEl);
        if (!colsRes.valid) { valid = false; } else { params.columns_to_drop = colsRes.value; }
        return { params, valid };
    }

    // --- Add Modal Listeners ---
    addModalApplyListener(applyFilterBtn, filterModal, filterModalEl, 'filter_rows', getFilterParams);
    addModalApplyListener(applySortBtn, sortModal, sortModalEl, 'sort_values', getSortParams);
    addModalApplyListener(applySplitBtn, splitModal, splitModalEl, 'split_column', getSplitParams);
    addModalApplyListener(applyCombineBtn, combineModal, combineModalEl, 'combine_columns', getCombineParams);
    addModalApplyListener(applyRenameBtn, renameModal, renameModalEl, 'rename_column', getRenameParams);

    if (applyDropBtn && dropModal && dropModalEl) {
        applyDropBtn.addEventListener('click', () => {
            if (confirm('Are you sure you want to permanently drop the selected columns?')) {
                const { params, valid } = getDropParams(dropModalEl);
                if (valid) {
                    performAction('/clean_operation', 'POST', { operation: 'drop_columns', params: params }, dropModal);
                }
            }
        });
    } else {
        if (!applyDropBtn) console.warn("Button for action 'drop_columns' not found.");
        if (!dropModalEl) console.warn("Modal element 'dropModalEl' not found.");
    }

    // --- Other Top-Level Listeners ---
    if (sidebar) { sidebar.addEventListener('click', handleSidebarClick); }
    if (undoBtn) undoBtn.addEventListener('click', () => performAction('/undo', 'POST'));
    if (redoBtn) redoBtn.addEventListener('click', () => performAction('/redo', 'POST'));
    if (saveBtn) saveBtn.addEventListener('click', () => {
        const filename = saveFilenameInput ? saveFilenameInput.value.trim() : '';
        performAction('/save', 'POST', filename ? { filename } : {});
    });
    // autoCleanBtn listener is ALREADY SET UP
    if (optimizeCategoriesBtn) optimizeCategoriesBtn.addEventListener('click', () => {
        if (confirm("Convert low-cardinality text columns to Category? (Can be undone)")) { performAction('/optimize_categories', 'POST'); }
    });

    const fillMissingMethodSelect = document.getElementById('fill-missing-method');
    if (fillMissingMethodSelect) { fillMissingMethodSelect.addEventListener('change', toggleFillValueInput); }


    // --- Initial State Update ---
    function updateInitialCounts() {
        // The backend now passes total_rows and total_columns, so this preview logic is less critical
        // but can serve as a fallback if those aren't available for some reason initially.
        if (rowCountSpan && rowCountSpan.textContent.includes('N/A') && tableContainer) {
            const initialRows = tableContainer.querySelectorAll('tbody > tr');
            rowCountSpan.textContent = `Rows: ${initialRows ? initialRows.length : 0} (Preview)`;
        }
    }
    updateInitialCounts();
    toggleFillValueInput();
    toggleOutlierMethodControls();
    loadAutoCleanConfigToForm(); // Load config values into the form
}); // End DOMContentLoaded