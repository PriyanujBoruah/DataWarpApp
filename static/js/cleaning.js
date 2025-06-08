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
    const rowCountSpan = document.getElementById('row-count');
    const colCountSpan = document.getElementById('col-count');
    const sidebar = document.querySelector('.sidebar');
    const toastContainer = document.querySelector('.toast-container');
    const sourceInfoDisplay = document.getElementById('source-info-display');
    const autoCleanBtn = document.getElementById('auto-clean-btn');
    const optimizeCategoriesBtn = document.getElementById('optimize-categories-btn');

    const outlierColumnSelect = document.getElementById('outlier-column');
    const outlierMethodSelect = document.getElementById('outlier-method-select');
    const outlierIqrControls = document.getElementById('outlier-iqr-controls');
    const outlierIqrFactorInput = document.getElementById('outlier-iqr-factor');
    const outlierZscoreControls = document.getElementById('outlier-zscore-controls');
    const outlierZscoreThresholdInput = document.getElementById('outlier-zscore-threshold');

    const showOutlierRangesBtn = document.getElementById('show-outlier-ranges-btn');
    const outlierRangesPanel = document.getElementById('outlier-ranges-panel');
    const outlierRangesLoading = document.getElementById('outlier-ranges-loading');
    const outlierRangesError = document.getElementById('outlier-ranges-error');
    const outlierRangesPlaceholder = document.getElementById('outlier-ranges-placeholder');
    const outlierRangesAccordion = document.getElementById('outlier-ranges-accordion');
    const outlierRangesPanelCloseBtn = document.getElementById('outlier-ranges-panel-close-btn');

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
    const configOutlierHandling = document.getElementById('config-outlier-handling');
    const configOutlierFactorGroup = document.getElementById('outlier-factor-group');
    const configOutlierIqrFactor = document.getElementById('config-outlier-iqr-factor');
    const configOutlierZscoreGroup = document.getElementById('outlier-zscore-group');
    const configOutlierZscoreThreshold = document.getElementById('config-outlier-zscore-threshold');

    const statsPanel = document.getElementById('stats-panel');
    const statsPanelContent = document.getElementById('stats-content');
    const statsPanelColumnName = document.getElementById('stats-panel-column-name');
    const statsPanelPlaceholder = document.getElementById('stats-panel-placeholder');
    const statsPanelLoading = document.getElementById('stats-panel-loading');
    const statsPanelError = document.getElementById('stats-panel-error');
    const statsPanelCloseBtn = document.getElementById('stats-panel-close-btn');
    const uniqueValuesSection = document.getElementById('unique-values-section');
    const uniqueValuesContainer = document.getElementById('unique-values-container');
    const uniqueValuesCountDisplay = document.getElementById('unique-values-count-display');
    const duplicateValuesSection = document.getElementById('duplicate-values-section');
    const duplicateValuesContainer = document.getElementById('duplicate-values-container');
    const duplicateValuesCountDisplay = document.getElementById('duplicate-values-count-display');

    const applyFilterBtn = document.getElementById('apply-filter-btn');
    const applySortBtn = document.getElementById('apply-sort-btn');
    const applySplitBtn = document.getElementById('apply-split-btn');
    const applyCombineBtn = document.getElementById('apply-combine-btn');
    const applyRenameBtn = document.getElementById('apply-rename-btn');
    const applyDropBtn = document.getElementById('apply-drop-btn');

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

    // --- Search DOM Elements ---
    const searchInput = document.getElementById('search-input');
    const searchColumnSelect = document.getElementById('search-column-select');
    const searchSuggestionsDatalist = document.getElementById('search-suggestions');
    const clearSearchBtn = document.getElementById('clear-search-btn');
    const searchStatusMessage = document.getElementById('search-status-message');

    // --- Formula Bar DOM Elements ---
    const formulaSelect = document.getElementById('formula-select');
    const formulaColumnSelect = document.getElementById('formula-column-select');
    const formulaRowStartInput = document.getElementById('formula-row-start');
    const formulaRowEndInput = document.getElementById('formula-row-end');
    const applyFormulaBtn = document.getElementById('apply-formula-btn');
    const formulaResultSpan = document.getElementById('formula-result');
    const formulaParamLabel = document.getElementById('formula-param-label'); // New
    const formulaParamInput = document.getElementById('formula-param-input'); // New


    // ==================================================
    // --- Helper Functions ---
    // ==================================================

    function showLoading(show = true) { // Default to show
        if (loadingIndicator) loadingIndicator.style.display = show ? 'block' : 'none';
        if (tableContainer) tableContainer.style.opacity = show ? '0.5' : '1';
    }

    function showLoadingIndicator(show) {
        if (loadingIndicator) {
            loadingIndicator.style.display = show ? 'block' : 'none';
        }
    }


    function getSelectedOptions(selectElement) {
        if (!selectElement) return [];
        return Array.from(selectElement.selectedOptions).map(option => option.value);
    }

    function displayToast(message, type = 'info') {
        const toastId = 'toast-' + Date.now();
        let bgColor = 'bg-primary';
        let textColor = 'text-white';

        if (type === 'success') {
            bgColor = 'bg-success';
        } else if (type === 'error') {
            bgColor = 'bg-danger';
        } else if (type === 'warning') {
            bgColor = 'bg-warning';
            textColor = 'text-dark';
        }

        const toastHTML = `
            <div id="${toastId}" class="toast align-items-center ${textColor} ${bgColor} border-0" role="alert" aria-live="assertive" aria-atomic="true">
              <div class="d-flex">
                <div class="toast-body">
                  ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
              </div>
            </div>
        `;
        if (toastContainer) {
            toastContainer.insertAdjacentHTML('beforeend', toastHTML);
            const toastElement = document.getElementById(toastId);
            if (toastElement) {
                const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
                toast.show();
                toastElement.addEventListener('hidden.bs.toast', () => {
                    toastElement.remove();
                });
            }
        } else {
            console.warn("Toast container not found. Message:", message);
        }
    }


    function handleError(errorData, status) {
        let errorMsg = 'An unknown error occurred.';
        if (errorData && errorData.error) {
            errorMsg = errorData.error;
        } else if (status) {
            errorMsg = `Request failed with status: ${status}`;
        } else if (errorData instanceof Error) {
            errorMsg = `Client-side error: ${errorData.message}`;
        }
        console.error('Error:', errorMsg, 'Status:', status, 'Data:', errorData);
        if (errorArea) errorArea.textContent = errorMsg;
        if (messageArea) messageArea.textContent = '';
        displayToast(errorMsg, 'error');
    }

    function updateTableAndStatus(data, modalToHide = null) {
        if (data.table_html && tableContainer) {
            if (Array.isArray(data.table_html) && data.table_html.length > 0) {
                 tableContainer.innerHTML = data.table_html[0];
                 if (rowCountSpan && data.table_html.length > 1) {
                     rowCountSpan.textContent = `Rows: ${data.table_html[1]}`;
                 }
                 if (colCountSpan && data.table_html.length > 2) {
                     colCountSpan.textContent = `Columns: ${data.table_html[2]}`;
                 }
            } else if (typeof data.table_html === 'string') {
                tableContainer.innerHTML = data.table_html;
            }
        }
        if (data.total_rows !== undefined && rowCountSpan) {
            rowCountSpan.textContent = `Rows: ${data.total_rows}`;
        }
        if (data.total_columns !== undefined && colCountSpan) {
            colCountSpan.textContent = `Columns: ${data.total_columns}`;
        }


        if (data.columns) {
            updateColumnSelectors(data.columns);
        }

        if (data.undo_redo_status) {
            updateUndoRedoButtons(data.undo_redo_status);
        }
        if (data.message) {
            const dfNotModified = data.df_modified === false;
            if (!dfNotModified) {
                 displayToast(data.message, 'success');
            }
            if (messageArea) messageArea.textContent = data.message;
            if (errorArea) errorArea.textContent = '';
            if (modalToHide && (!data.error || dfNotModified)) {
                modalToHide.hide();
            }
        }
        if (data.error) {
            handleError(data, null);
        }


        if (data.saved_filename) {
            if (saveFilenameInput) saveFilenameInput.value = data.saved_filename;
        }

        if (searchStatusMessage) {
            if (data.search_applied) {
                searchStatusMessage.textContent = `Filtered: ${data.filtered_row_count} of ${data.original_row_count} rows match '${data.search_term_applied}' in '${data.search_column_applied}'.`;
                searchStatusMessage.style.display = 'inline';
                if (clearSearchBtn) clearSearchBtn.style.display = 'inline-block';
            } else if (data.search_cleared) {
                searchStatusMessage.textContent = 'Search cleared.';
                searchStatusMessage.style.display = 'inline';
                setTimeout(() => { if(searchStatusMessage) searchStatusMessage.style.display = 'none'; }, 3000);
                if (clearSearchBtn) clearSearchBtn.style.display = 'none';
            }
        }
    }


    function updateColumnSelectors(columns) {
        const selects = document.querySelectorAll('select');
        selects.forEach(select => {
            if (select.id && (
                select.id.includes('-column') ||
                select.id.includes('-cols') ||
                select.id.includes('-name') ||
                select.id.includes('search-column-select') ||
                select.id.includes('formula-column-select') ||
                select.multiple
            )) {
                const currentValues = select.multiple ? getSelectedOptions(select) : [select.value];
                let placeholderOption = select.querySelector('option[value=""][disabled]');
                if (!placeholderOption) {
                    placeholderOption = select.querySelector('option[value=""]');
                }

                const optionsHtml = columns.map(col =>
                    `<option value="${col}">${col}</option>`
                ).join('');

                select.innerHTML = '';
                if (placeholderOption) {
                    select.appendChild(placeholderOption.cloneNode(true));
                }
                select.insertAdjacentHTML('beforeend', optionsHtml);

                if (select.multiple) {
                    Array.from(select.options).forEach(option => {
                        if (currentValues.includes(option.value)) {
                            option.selected = true;
                        }
                    });
                } else {
                    if (columns.includes(currentValues[0])) {
                        select.value = currentValues[0];
                    } else if (placeholderOption) {
                        select.value = placeholderOption.value;
                    }
                }
            }
        });
    }


    function updateUndoRedoButtons(status) {
        if (undoBtn) undoBtn.disabled = !status.undo_enabled;
        if (redoBtn) redoBtn.disabled = !status.redo_enabled;
    }

    function getRequiredValue(elementId, paramName, isSelect = false, isMultiSelect = false, context = document) {
        const element = context.querySelector(`#${elementId}`);
        if (!element) {
            console.error(`Element ${elementId} not found in context:`, context);
            return { value: null, valid: false, msg: `Config error: ${elementId} missing.` };
        }

        let value;
        let valid = true;
        let msg = '';

        if (isMultiSelect) {
            value = getSelectedOptions(element);
            if (element.required && (!value || value.length === 0)) {
                valid = false;
                msg = `Select at least one option for ${paramName}.`;
            }
        } else {
            value = element.value;
            if (isSelect) {
                if (element.required && !value) {
                    valid = false;
                    msg = `Select an option for ${paramName}.`;
                }
            } else {
                if (element.required && value.trim() === '') {
                    valid = false;
                    msg = `Enter a value for ${paramName}.`;
                }
            }
        }
        return { value: valid ? value : null, valid, msg };
    }


    function getOptionalValue(elementId, paramName, defaultValue = null, context = document) {
        const element = context.querySelector(`#${elementId}`);
        return (element && element.value.trim()) ? element.value.trim() : defaultValue;
    }

    function getCheckboxValue(elementId, paramName, context = document) {
        const element = context.querySelector(`#${elementId}`);
        return element ? element.checked : false;
    }

    function toggleFillValueInput() {
        const fillMissingMethodSelect = document.getElementById('fill-missing-method');
        const fillValueInputGroup = document.getElementById('fill-value-input-group');
        const fillValueInput = document.getElementById('fill-missing-value');

        if (fillMissingMethodSelect && fillValueInputGroup) {
            if (fillMissingMethodSelect.value === 'value') {
                fillValueInputGroup.style.display = '';
                if (fillValueInput) fillValueInput.required = true;
            } else {
                fillValueInputGroup.style.display = 'none';
                if (fillValueInput) {
                    fillValueInput.required = false;
                    fillValueInput.value = '';
                }
            }
        }
    }


    function toggleRightPanel(panelToShow) {
        const panels = [statsPanel, autoCleanConfigPanel, outlierRangesPanel];
        panels.forEach(panel => {
            if (panel) {
                if (panel === panelToShow && panel.style.display !== 'block') {
                    panel.style.display = 'block';
                } else if (panel !== panelToShow) {
                    panel.style.display = 'none';
                } else {
                    panel.style.display = 'none';
                }
            }
        });
        if (panels.every(p => !p || p.style.display === 'none') && activeColumnHeader) {
            activeColumnHeader.classList.remove('active-stat-col');
            activeColumnHeader = null;
        }
    }


    async function fetchAndDisplayOutlierRanges() {
        if (!outlierRangesPanel || !outlierRangesAccordion || !outlierRangesLoading || !outlierRangesError || !outlierRangesPlaceholder) {
            console.error("Outlier ranges panel elements not found.");
            return;
        }
        if (outlierRangesPanel.style.display === 'block') {
            toggleRightPanel(null);
            return;
        }
        toggleRightPanel(outlierRangesPanel);

        outlierRangesAccordion.innerHTML = '';
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
            } else if (data.message) {
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
        outlierRangesAccordion.innerHTML = '';

        Object.entries(rangesData).forEach(([colName, colRangeInfo], index) => {
            const uniqueId = `range-${colName.replace(/[^a-zA-Z0-9]/g, "")}-${index}`;

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


    function getAutoCleanConfigValues() {
        const config = {};
        if (configOutlierHandling) config.outlier_handling = configOutlierHandling.value;
        if (configOutlierIqrFactor) config.outlier_iqr_factor = parseFloat(configOutlierIqrFactor.value) || 1.5;
        if (configOutlierZscoreThreshold) config.outlier_zscore_threshold = parseFloat(configOutlierZscoreThreshold.value) || 3.0;

        if (configMissingNumeric) config.missing_numeric_method = configMissingNumeric.value;
        if (configMissingOther) config.missing_other_method = configMissingOther.value;
        if (configCaseChange) config.case_change_method = configCaseChange.value;

        if (configTrimWhitespace) config.trim_whitespace = configTrimWhitespace.checked;
        if (configConvertNumeric) config.convert_numeric = configConvertNumeric.checked;
        if (configConvertDatetime) config.convert_datetime = configConvertDatetime.checked;
        if (configConvertCategory) config.convert_category = configConvertCategory.checked;
        return config;
    }

    async function loadAutoCleanConfigToForm() {
        try {
            const response = await fetch('/get_auto_clean_config');
            if (!response.ok) {
                console.error('Failed to fetch auto-clean config:', response.status);
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
        } finally {
            if (configOutlierHandling) {
                toggleOutlierParameterVisibility();
            }
        }
    }


    function toggleOutlierParameterVisibility() {
        if (configOutlierHandling && configOutlierFactorGroup && configOutlierZscoreGroup) {
            const selectedMethod = configOutlierHandling.value;
            if (selectedMethod === 'clip_iqr' || selectedMethod === 'remove_iqr') {
                configOutlierFactorGroup.style.display = 'block';
                configOutlierZscoreGroup.style.display = 'none';
            } else if (selectedMethod === 'clip_zscore' || selectedMethod === 'remove_zscore') {
                configOutlierFactorGroup.style.display = 'none';
                configOutlierZscoreGroup.style.display = 'block';
            } else {
                configOutlierFactorGroup.style.display = 'none';
                configOutlierZscoreGroup.style.display = 'none';
            }
        }
    }


    function toggleOutlierMethodControls() {
        if (outlierMethodSelect && outlierIqrControls && outlierZscoreControls) {
            const selectedMethod = outlierMethodSelect.value;
            if (selectedMethod === 'iqr') {
                outlierIqrControls.style.display = 'flex';
                outlierZscoreControls.style.display = 'none';
            } else if (selectedMethod === 'zscore') {
                outlierIqrControls.style.display = 'none';
                outlierZscoreControls.style.display = 'flex';
            } else {
                outlierIqrControls.style.display = 'none';
                outlierZscoreControls.style.display = 'none';
            }
        }
    }

    let activeColumnHeader = null;

    async function fetchAndDisplayColumnStats(columnName) {
        if (!statsPanel || !statsPanelContent || !statsPanelColumnName || !statsPanelLoading || !statsPanelError || !statsPanelPlaceholder) {
            console.error("Stats panel elements not found.");
            return;
        }
        if (statsPanel.style.display === 'block' && activeColumnHeader && activeColumnHeader.textContent.trim() === columnName) {
            toggleRightPanel(null);
            return;
        }

        toggleRightPanel(statsPanel);

        statsPanelColumnName.textContent = `Stats: ${columnName}`;
        statsPanelPlaceholder.style.display = 'none';
        statsPanelError.style.display = 'none';
        statsPanelContent.innerHTML = '';
        statsPanelLoading.style.display = 'block';

        if (uniqueValuesSection) uniqueValuesSection.style.display = 'none';
        if (duplicateValuesSection) duplicateValuesSection.style.display = 'none';


        try {
            const response = await fetch(`/column_stats/${encodeURIComponent(columnName)}`);
            const data = await response.json();
            statsPanelLoading.style.display = 'none';

            if (!response.ok) {
                throw new Error(data.error || `Failed to fetch stats (Status: ${response.status})`);
            }

            if (data.stats) {
                updateStatsPanel(columnName, data, data.dtype);
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
        const stats = statsData.stats;
        if (!statsPanelContent || !statsPanelColumnName || !statsPanelPlaceholder ||
            !uniqueValuesSection || !uniqueValuesContainer || !uniqueValuesCountDisplay ||
            !duplicateValuesSection || !duplicateValuesContainer || !duplicateValuesCountDisplay) {
            console.error("One or more stats panel elements are missing for updateStatsPanel.");
            return;
        }

        statsPanelColumnName.textContent = `Stats: ${columnName}`;
        statsPanelPlaceholder.style.display = 'none';
        statsPanelContent.innerHTML = '';

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
                    value = Object.entries(value).map(([k, v]) => `${k}: ${v}`).join(', ');
                } else {
                    value = (value === null || value === undefined || String(value).toLowerCase() === 'nan' || String(value) === '<na>') ? 'NULL' : value;
                }
                valueSpan.textContent = String(value);

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
                    valueSpan.textContent = (String(value).toLowerCase() === 'nan' || String(value).toLowerCase() === 'null' || String(value) === '<na>') ? 'NULL' : String(value);
                    li.appendChild(valueSpan);
                    ul.appendChild(li);
                });
                uniqueValuesContainer.innerHTML = '';
                uniqueValuesContainer.appendChild(ul);

                let countText = `Showing ${uniqueSample.length}`;
                if (totalUniqueCount !== undefined) {
                    countText += ` of ${totalUniqueCount} total value(s) that appear only once.`;
                }
                uniqueValuesCountDisplay.textContent = countText;

                if (totalUniqueCount > uniqueSample.length) {
                    const p = document.createElement('p');
                    p.className = 'text-muted small mt-1 fst-italic';
                    p.textContent = `...and ${totalUniqueCount - uniqueSample.length} more.`;
                    uniqueValuesContainer.appendChild(p);
                }
            } else {
                uniqueValuesContainer.innerHTML = '<p class="placeholder-text">No values appear only once (or column is empty/all values are duplicated).</p>';
                 if (totalUniqueCount !== undefined) {
                    uniqueValuesCountDisplay.textContent = `Total values appearing once: ${totalUniqueCount}.`;
                }
            }
        } else {
            uniqueValuesContainer.innerHTML = '<p class="placeholder-text">Unique value data not available.</p>';
        }

        // --- MODIFIED: Display Duplicate Values with Percentages ---
        duplicateValuesContainer.innerHTML = '<p class="placeholder-text">Loading duplicate values...</p>';
        duplicateValuesCountDisplay.textContent = '';
        const duplicatesSample = stats['duplicate_values_sample'];
        const totalDistinctDuplicates = stats['duplicate_values_distinct_count'];
        const totalDuplicateOccurrences = stats['duplicate_occurrences_total'];
        const totalDuplicatePercentage = stats['duplicate_occurrences_percentage']; // New from backend

        if (duplicatesSample && Array.isArray(duplicatesSample)) {
            duplicateValuesSection.style.display = 'block';
            if (duplicatesSample.length > 0) {
                const ul = document.createElement('ul');
                duplicatesSample.forEach(item => { // item is now [value_string, count, percentage_string]
                    const valueStr = item[0];
                    const count = item[1];
                    const percentageStr = item[2];

                    const li = document.createElement('li');

                    const valueSpan = document.createElement('span');
                    valueSpan.className = 'value-item';
                    valueSpan.textContent = (String(valueStr).toLowerCase() === 'nan' || String(valueStr).toLowerCase() === 'null' || String(valueStr) === '<na>') ? 'NULL' : String(valueStr);
                    li.appendChild(valueSpan);

                    const detailsSpan = document.createElement('span'); // Wrapper for count and percentage
                    detailsSpan.style.display = 'flex';
                    detailsSpan.style.alignItems = 'center';
                    detailsSpan.style.marginLeft = '10px';

                    const countSpan = document.createElement('span');
                    countSpan.className = 'count-item';
                    countSpan.textContent = count;
                    detailsSpan.appendChild(countSpan);

                    const percentageSpan = document.createElement('span');
                    percentageSpan.textContent = ` (${percentageStr})`;
                    percentageSpan.style.fontSize = '0.9em';
                    percentageSpan.style.color = '#6c757d';
                    percentageSpan.style.marginLeft = '4px';
                    detailsSpan.appendChild(percentageSpan);

                    li.appendChild(detailsSpan);
                    ul.appendChild(li);
                });
                duplicateValuesContainer.innerHTML = '';
                duplicateValuesContainer.appendChild(ul);

                let countText = `Showing ${duplicatesSample.length}`;
                if (totalDistinctDuplicates !== undefined) {
                    countText += ` of ${totalDistinctDuplicates} distinct duplicated value(s). `;
                }
                if (totalDuplicateOccurrences !== undefined && totalDuplicatePercentage !== undefined) {
                    countText += `Total occurrences: ${totalDuplicateOccurrences} (${totalDuplicatePercentage} of all rows).`;
                }
                duplicateValuesCountDisplay.textContent = countText;


                if (totalDistinctDuplicates > duplicatesSample.length) {
                    const p = document.createElement('p');
                    p.className = 'text-muted small mt-1 fst-italic';
                    p.textContent = `...and ${totalDistinctDuplicates - duplicatesSample.length} more distinct duplicated values.`;
                    duplicateValuesContainer.appendChild(p);
                }
            } else {
                duplicateValuesContainer.innerHTML = '<p class="placeholder-text">No duplicate values found (all values appear at most once).</p>';
                if (totalDistinctDuplicates !== undefined) {
                    duplicateValuesCountDisplay.textContent = `Total distinct duplicated values: ${totalDistinctDuplicates}.`;
                }
            }
        } else {
            duplicateValuesContainer.innerHTML = '<p class="placeholder-text">Duplicate value data not available.</p>';
        }
        // --- END MODIFICATION ---

        statsPanel.style.display = 'block';
        statsPanelLoading.style.display = 'none';
        statsPanelError.style.display = 'none';
    }


    function handleColumnHeaderClick(event) {
        const th = event.target.closest('th');
        if (th && th.parentElement && th.parentElement.parentElement && th.parentElement.parentElement.tagName === 'THEAD' && tableContainer.contains(th)) {
            const columnName = th.textContent.trim();
            if (columnName && columnName !== '#') {
                if (!activeColumnHeader || activeColumnHeader !== th || statsPanel.style.display !== 'block') {
                    if (activeColumnHeader) {
                        activeColumnHeader.classList.remove('active-stat-col');
                    }
                    th.classList.add('active-stat-col');
                    activeColumnHeader = th;
                    fetchAndDisplayColumnStats(columnName);
                } else {
                    toggleRightPanel(null);
                }
            }
        }
    }


    async function performAction(url, method = 'POST', body = null, modalInstance = null) {
        showLoading();
        if (messageArea) messageArea.textContent = '';
        if (errorArea) errorArea.textContent = '';
        let responseData = {};

        try {
            const fetchOptions = {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                body: body ? JSON.stringify(body) : null
            };

            const response = await fetch(url, fetchOptions);

            try {
                responseData = await response.json();
            } catch (e) {
                if (!response.ok) {
                    throw {
                        errorData: { error: `Status ${response.status} with non-JSON response. Server might be down or returned HTML error.` },
                        status: response.status
                    };
                }
                responseData = { message: "Received OK response but could not parse JSON body." };
            }

            if (!response.ok) {
                throw { errorData: responseData, status: response.status };
            }
            updateTableAndStatus(responseData, modalInstance);

        } catch (errorInfo) {
            handleError(errorInfo.errorData || errorInfo, errorInfo.status);
        } finally {
            showLoading(false);
        }
    }

    // --- SEARCH FUNCTIONALITY ---
    function debounce(func, delay) {
        let timeout;
        return function(...args) {
            const context = this;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), delay);
        };
    }

    async function fetchSuggestions() {
        if (!searchInput || !searchColumnSelect || !searchSuggestionsDatalist) return;

        const query = searchInput.value;
        const column = searchColumnSelect.value;

        if (query.length < 1 || !column) {
            searchSuggestionsDatalist.innerHTML = '';
            return;
        }

        try {
            const response = await fetch(`/get_suggestions?column=${encodeURIComponent(column)}&query=${encodeURIComponent(query)}`);
            if (!response.ok) {
                console.error('Suggestion fetch failed');
                searchSuggestionsDatalist.innerHTML = '';
                return;
            }
            const data = await response.json();
            searchSuggestionsDatalist.innerHTML = '';
            if (data.suggestions) {
                data.suggestions.forEach(item => {
                    const option = document.createElement('option');
                    option.value = item;
                    searchSuggestionsDatalist.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error fetching suggestions:', error);
            searchSuggestionsDatalist.innerHTML = '';
        }
    }

    const debouncedFetchSuggestions = debounce(fetchSuggestions, 300);


    async function triggerSearch() {
        if (!searchInput || !searchColumnSelect) return;

        const term = searchInput.value;
        const column = searchColumnSelect.value;

        if (!column && term) {
            displayToast('Please select a column to search in.', 'warning');
            return;
        }
        const body = { column: column, term: term };
        performAction('/perform_search', 'POST', body);
    }


    async function clearSearch() {
        if (!searchInput || !searchColumnSelect || !searchStatusMessage || !clearSearchBtn) return;
        performAction('/clear_search_filter', 'POST');

        searchInput.value = '';
        if (searchColumnSelect.options.length > 0) {
            searchColumnSelect.selectedIndex = 0;
        }
        if(searchSuggestionsDatalist) searchSuggestionsDatalist.innerHTML = '';
    }


    if (searchInput) {
        searchInput.addEventListener('input', debouncedFetchSuggestions);
        searchInput.addEventListener('keypress', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                triggerSearch();
            }
        });
    }
    if (searchColumnSelect) {
        searchColumnSelect.addEventListener('change', () => {
            if (searchInput && searchInput.value) {
                triggerSearch();
            }
            if (searchInput && searchInput.value) {
                fetchSuggestions();
            } else if (searchSuggestionsDatalist) {
                searchSuggestionsDatalist.innerHTML = '';
            }
        });
    }
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', clearSearch);
    }
    // --- END SEARCH FUNCTIONALITY ---

    // --- Formula Bar Logic (Updated for Parameter Input) ---
    if (formulaSelect && formulaParamLabel && formulaParamInput && formulaColumnSelect && applyFormulaBtn && formulaResultSpan) {
        formulaSelect.addEventListener('change', async function() {
            const selectedFormula = this.value;

            // Reset and hide dependent elements
            formulaColumnSelect.innerHTML = '<option value="" selected disabled>-- Select Column --</option>';
            formulaColumnSelect.style.display = 'none';
            formulaRowStartInput.style.display = 'none';
            formulaRowStartInput.value = '';
            formulaRowEndInput.style.display = 'none';
            formulaRowEndInput.value = '';
            applyFormulaBtn.style.display = 'none';
            formulaResultSpan.style.display = 'none';
            formulaResultSpan.textContent = '';
            formulaResultSpan.className = 'ms-2 small flex-shrink-0';

            // Handle parameter input visibility and label
            formulaParamLabel.style.display = 'none';
            formulaParamInput.style.display = 'none';
            formulaParamInput.value = '';
            formulaParamInput.placeholder = 'Param';
            formulaParamInput.type = 'text';

            if (selectedFormula === 'PERCENTILE') {
                formulaParamLabel.textContent = 'P (0-100):';
                formulaParamInput.placeholder = 'e.g., 90';
                formulaParamInput.type = 'number'; // Use number type for better input
                formulaParamLabel.style.display = 'inline-block';
                formulaParamInput.style.display = 'inline-block';
            } else if (selectedFormula === 'COUNT_REGEX') {
                formulaParamLabel.textContent = 'Regex:';
                formulaParamInput.placeholder = 'Pattern';
                formulaParamInput.type = 'text';
                formulaParamLabel.style.display = 'inline-block';
                formulaParamInput.style.display = 'inline-block';
            }
            // Add more else if for other formulas needing parameters here

            if (selectedFormula) {
                showLoadingIndicator(true);
                try {
                    const response = await fetch(`/get_valid_columns_for_formula?formula=${selectedFormula}`);
                    if (!response.ok) {
                        const errorData = await response.json();
                        displayToast(`Error fetching columns: ${errorData.error || response.statusText}`, 'error');
                        return; // Keep loading indicator until resolved or error shown
                    }
                    const data = await response.json();
                    const validColumns = data.columns || [];

                    if (validColumns.length === 0) {
                        displayToast(`No valid columns for formula '${selectedFormula}'.`, 'warning');
                        return;
                    }

                    validColumns.forEach(colName => {
                        const option = document.createElement('option');
                        option.value = colName;
                        option.textContent = colName;
                        formulaColumnSelect.appendChild(option);
                    });

                    formulaColumnSelect.style.display = 'inline-block';
                    formulaRowStartInput.style.display = 'inline-block';
                    formulaRowEndInput.style.display = 'inline-block';
                    applyFormulaBtn.style.display = 'inline-block';

                } catch (error) {
                    console.error('Error fetching valid columns for formula:', error);
                    displayToast('Failed to fetch valid columns. Check console.', 'error');
                } finally {
                    showLoadingIndicator(false);
                }
            }
        });
    }

    if (applyFormulaBtn) {
        applyFormulaBtn.addEventListener('click', async function() {
            const formula = formulaSelect.value;
            const column = formulaColumnSelect.value;
            const rowStartStr = formulaRowStartInput.value;
            const rowEndStr = formulaRowEndInput.value;
            let parameter = null;

            if (!formula || !column) {
                displayToast('Please select a formula and a column.', 'warning');
                return;
            }

            if (formulaParamInput.style.display !== 'none') {
                parameter = formulaParamInput.value;
                if (parameter.trim() === '') {
                    displayToast(`Parameter for ${formula} is required.`, 'warning');
                    return;
                }
                if (formula === 'PERCENTILE') {
                    const pVal = parseFloat(parameter);
                    if (isNaN(pVal) || pVal < 0 || pVal > 100) {
                        displayToast('Percentile (P) must be a number between 0 and 100.', 'warning');
                        return;
                    }
                    parameter = pVal;
                }
            }

            const rowStart = rowStartStr ? parseInt(rowStartStr) : null;
            const rowEnd = rowEndStr ? parseInt(rowEndStr) : null;

            if (rowStartStr && (isNaN(rowStart) || rowStart < 1)) {
                displayToast('Start row must be a positive number.', 'warning'); return;
            }
            if (rowEndStr && (isNaN(rowEnd) || rowEnd < 1)) {
                displayToast('End row must be a positive number.', 'warning'); return;
            }
            if (rowStart !== null && rowEnd !== null && rowStart > rowEnd) {
                displayToast('Start row cannot be greater than end row.', 'warning'); return;
            }

            formulaResultSpan.textContent = 'Calculating...';
            formulaResultSpan.className = 'ms-2 small flex-shrink-0';
            formulaResultSpan.style.display = 'inline-block';
            applyFormulaBtn.disabled = true;
            showLoadingIndicator(true);

            try {
                const response = await fetch('/apply_formula', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', },
                    body: JSON.stringify({
                        formula: formula,
                        column_name: column,
                        row_start: rowStart,
                        row_end: rowEnd,
                        parameter: parameter
                    })
                });
                const data = await response.json();
                if (!response.ok) {
                    formulaResultSpan.textContent = `Error: ${data.error || 'Failed'}`;
                    formulaResultSpan.className = 'ms-2 small flex-shrink-0 text-danger';
                    displayToast(data.error || 'Formula calculation failed.', 'error');
                } else {
                    formulaResultSpan.textContent = `${data.result}`;
                    formulaResultSpan.className = 'ms-2 small flex-shrink-0 text-success';
                }
            } catch (error) {
                console.error('Error applying formula:', error);
                formulaResultSpan.textContent = 'Error!';
                formulaResultSpan.className = 'ms-2 small flex-shrink-0 text-danger';
                displayToast('An error occurred while applying formula. Check console.', 'error');
            } finally {
                 applyFormulaBtn.disabled = false;
                 showLoadingIndicator(false);
            }
        });
    }
    // --- End Formula Bar Logic ---


    // --- Event Listeners Setup ---
    if (outlierMethodSelect) { outlierMethodSelect.addEventListener('change', toggleOutlierMethodControls); }
    if (showOutlierRangesBtn) { showOutlierRangesBtn.addEventListener('click', fetchAndDisplayOutlierRanges); }
    if (outlierRangesPanelCloseBtn) { outlierRangesPanelCloseBtn.addEventListener('click', () => { toggleRightPanel(null); }); }
    if (statsPanelCloseBtn) { statsPanelCloseBtn.addEventListener('click', () => { toggleRightPanel(null); }); }
    if (toggleConfigPanelBtn) { toggleConfigPanelBtn.addEventListener('click', () => { toggleRightPanel(autoCleanConfigPanel); }); }
    if (configPanelCloseBtn) { configPanelCloseBtn.addEventListener('click', () => { toggleRightPanel(null); }); }
    if (configOutlierHandling) { configOutlierHandling.addEventListener('change', toggleOutlierParameterVisibility); }


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
                    console.log("Saved config:", data.config);
                } else {
                    handleError(data, response.status);
                }
            } catch (error) {
                handleError(error, null);
            }
            finally {
                showLoading(false);
            }
        });
    }


    if (tableContainer) {
        tableContainer.addEventListener('click', handleColumnHeaderClick);
    }
    if (autoCleanBtn) {
        autoCleanBtn.addEventListener('click', () => {
            if (confirm("Apply Auto Clean with current configuration? (This action can be undone)")) {
                performAction('/auto_clean', 'POST');
            }
        });
    }

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
        const controlGroup = button.closest('.cleaning-control-content') || button.closest('.cleaning-control') || sidebar;


        try {
            if (action === 'remove_duplicates') {
            } else if (action === 'remove_missing') {
                params.how = button.dataset.params ? JSON.parse(button.dataset.params).how : 'any';
            } else if (action === 'fill_missing') {
                params.method = controlGroup.querySelector('#fill-missing-method')?.value || 'value';
                const colSelect = controlGroup.querySelector('#fill-missing-column');
                params.column = colSelect ? (colSelect.value || null) : null;
                if (params.column === "") params.column = null;

                if (params.method === 'value') {
                    const valueInputEl = controlGroup.querySelector('#fill-missing-value');
                    if (valueInputEl) {
                        params.value = valueInputEl.value;
                    } else {
                        displayToast("Fill value input not found.", "error");
                        validationOk = false;
                    }
                }
            } else if (action === 'remove_spaces') {
                const colRes = getRequiredValue('remove-spaces-column', 'Column', true, false, controlGroup);
                if (!colRes.valid) validationOk = false; else params.column = colRes.value;
            } else if (action === 'change_dtype') {
                const colRes = getRequiredValue('change-dtype-column', 'Column', true, false, controlGroup);
                const typeRes = getRequiredValue('change-dtype-target-type', 'Target Type', true, false, controlGroup);
                if (!colRes.valid || !typeRes.valid) validationOk = false;
                else { params.column = colRes.value; params.target_type = typeRes.value; }
            } else if (action === 'fix_datetime') {
                const colRes = getRequiredValue('fix-datetime-column', 'Column', true, false, controlGroup);
                if (!colRes.valid) validationOk = false; else params.column = colRes.value;
                params.format = getOptionalValue('fix-datetime-format', 'format', null, controlGroup);
            } else if (action === 'check_id_uniqueness') {
                const colRes = getRequiredValue('check-id-uniqueness-column', 'Column', true, false, controlGroup);
                if (!colRes.valid) validationOk = false; else params.column = colRes.value;
            } else if (action === 'check_id_format') {
                const colRes = getRequiredValue('check-id-format-column', 'Column', true, false, controlGroup);
                const patternRes = getRequiredValue('check-id-format-pattern', 'Pattern', false, false, controlGroup);
                if (!colRes.valid || !patternRes.valid) {
                    validationOk = false;
                    if (patternRes.msg) displayToast(patternRes.msg, 'warning');
                } else { params.column = colRes.value; params.pattern = patternRes.value.trim(); }
            } else if (action.includes('outliers_iqr') || action.includes('outliers_zscore')) {
                const colResult = getRequiredValue('outlier-column', 'Column', true, false, controlGroup);
                if (!colResult.valid) { validationOk = false; displayToast(colResult.msg, 'warning'); }
                else {
                    params.column = colResult.value;
                    if (action.includes('iqr')) {
                        const factorResult = getRequiredValue('outlier-iqr-factor', 'IQR Factor', false, false, document.getElementById('outlier-iqr-controls'));
                        if (!factorResult.valid) { validationOk = false; displayToast(factorResult.msg, 'warning'); }
                        else params.factor = parseFloat(factorResult.value);
                    } else if (action.includes('zscore')) {
                        const thresholdResult = getRequiredValue('outlier-zscore-threshold', 'Z-score Threshold', false, false, document.getElementById('outlier-zscore-controls'));
                        if (!thresholdResult.valid) { validationOk = false; displayToast(thresholdResult.msg, 'warning');}
                        else params.threshold = parseFloat(thresholdResult.value);
                    }
                }
            } else if (action === 'replace_text') {
                const colRes = getRequiredValue('replace-text-column', 'Column', true, false, controlGroup);
                if (!colRes.valid) validationOk = false; else params.column = colRes.value;

                const findInputEl = controlGroup.querySelector('#replace-text-find');
                if (findInputEl) { params.text_to_find = findInputEl.value; }
                else { displayToast("Find text input not found.", "error"); validationOk = false; }

                const replaceWithEl = controlGroup.querySelector('#replace-text-replace');
                if (replaceWithEl) { params.replace_with = replaceWithEl.value; }
                else { params.replace_with = ''; }

                params.use_regex = getCheckboxValue('replace-text-regex', 'use_regex', controlGroup);

            } else if (action === 'change_case') {
                const colRes = getRequiredValue('change-case-column', 'Column', true, false, controlGroup);
                const typeRes = getRequiredValue('change-case-type', 'Case Type', true, false, controlGroup);
                if (!colRes.valid || !typeRes.valid) validationOk = false;
                else { params.column = colRes.value; params.case_type = typeRes.value; }
            } else if (action === 'map_values') {
                const colRes = getRequiredValue('map-values-column', 'Column', true, false, controlGroup);
                const mapStrRes = getRequiredValue('map-values-dict', 'Mapping Dictionary (JSON)', false, false, controlGroup);
                if (!colRes.valid || !mapStrRes.valid) {
                    validationOk = false;
                    if (mapStrRes.msg) displayToast(mapStrRes.msg, 'warning');
                } else {
                    params.column = colRes.value;
                    try {
                        params.mapping_dict = JSON.parse(mapStrRes.value);
                    } catch (e) {
                        displayToast(`Invalid JSON for mapping: ${e.message}`, 'error');
                        validationOk = false;
                    }
                }
            }
        } catch (e) {
            console.error("Error gathering parameters from sidebar for action " + action + ":", e);
            displayToast("Client-side error processing parameters.", "error");
            validationOk = false;
        }

        if (validationOk) {
            performAction('/clean_operation', 'POST', body);
        }
    }


    function addModalApplyListener(button, modalInstance, modalElement, action, paramGetterFn) {
        if (!modalElement) {
            console.warn(`Modal element not provided for action "${action}". Listener not attached.`);
            return;
        }
        if (button && modalInstance) {
            button.addEventListener('click', () => {
                const { params, valid, msg } = paramGetterFn(modalElement);
                if (valid) {
                    const body = { operation: action, params: params };
                    performAction('/clean_operation', 'POST', body, modalInstance);
                } else if (msg) {
                    displayToast(msg, 'warning');
                }
            });
        } else {
            if (!button) console.warn(`Button for modal action "${action}" not found.`);
        }
    }


    function getFilterParams(modalEl) {
        let params = {};
        let valid = true;
        let validationMessages = [];

        const colRes = getRequiredValue('modal-filter-column', 'Column', true, false, modalEl);
        if (!colRes.valid) { valid = false; validationMessages.push(colRes.msg); }
        else params.column = colRes.value;

        const condRes = getRequiredValue('modal-filter-condition', 'Condition', true, false, modalEl);
        if (!condRes.valid) { valid = false; validationMessages.push(condRes.msg); }
        else params.condition = condRes.value;

        params.action = getOptionalValue('modal-filter-action', 'action', 'keep', modalEl);

        if (valid && !['isnull', 'notnull'].includes(params.condition)) {
            const valueInput = modalEl.querySelector('#modal-filter-value');
            if (!valueInput) {
                 valid = false; validationMessages.push("Filter value input not found.");
            } else {
                params.value = valueInput.value;
            }
        } else if (valid) {
            params.value = null;
            const enteredValue = getOptionalValue('modal-filter-value', 'value', null, modalEl);
            if (enteredValue !== null && enteredValue !== '') {
                displayToast("Value entered but condition is 'Is Null' or 'Is Not Null'. Value will be ignored.", 'info');
            }
        }
        return { params, valid, msg: validationMessages.join(' ') };
    }

    function getSortParams(modalEl) {
        let params = {};
        let valid = true;
        let validationMessages = [];
        const colsRes = getRequiredValue('modal-sort-cols', 'Columns', false, true, modalEl);
        if (!colsRes.valid) { valid = false; validationMessages.push(colsRes.msg); }
        else {
            params.columns_to_sort_by = colsRes.value;
            params.ascending = (getOptionalValue('modal-sort-ascending', 'ascending', 'true', modalEl) === 'true');
        }
        return { params, valid, msg: validationMessages.join(' ') };
    }

    function getSplitParams(modalEl) {
        let params = {};
        let valid = true;
        let validationMessages = [];
        const colRes = getRequiredValue('modal-split-column', 'Column', true, false, modalEl);
        const delimRes = getRequiredValue('modal-split-delimiter', 'Delimiter', false, false, modalEl);
        if (!colRes.valid) { valid = false; validationMessages.push(colRes.msg); }
        if (!delimRes.valid) { valid = false; validationMessages.push(delimRes.msg); }
        if (valid) {
            params.column = colRes.value;
            params.delimiter = delimRes.value.trim();
            params.new_column_names = getOptionalValue('modal-split-new-names', 'new_column_names', null, modalEl);
        }
        return { params, valid, msg: validationMessages.join(' ') };
    }

    function getCombineParams(modalEl) {
        let params = {};
        let valid = true;
        let validationMessages = [];
        const colsRes = getRequiredValue('modal-combine-cols', 'Columns', false, true, modalEl);
        const nameRes = getRequiredValue('modal-combine-new-name', 'New Name', false, false, modalEl);
        if (!colsRes.valid) { valid = false; validationMessages.push(colsRes.msg); }
        else if (colsRes.value.length < 2) { valid = false; validationMessages.push('Select at least two columns to combine.');}
        if (!nameRes.valid) { valid = false; validationMessages.push(nameRes.msg); }

        if (valid) {
            params.columns_to_combine = colsRes.value;
            params.new_column_name = nameRes.value.trim();
            params.separator = getOptionalValue('modal-combine-separator', 'separator', '', modalEl);
        }
        return { params, valid, msg: validationMessages.join(' ') };
    }

    function getRenameParams(modalEl) {
        let params = {};
        let valid = true;
        let validationMessages = [];
        const oldNameRes = getRequiredValue('modal-rename-old-name', 'Column', true, false, modalEl);
        const newNameRes = getRequiredValue('modal-rename-new-name', 'New Name', false, false, modalEl);
        if (!oldNameRes.valid) { valid = false; validationMessages.push(oldNameRes.msg); }
        if (!newNameRes.valid) { valid = false; validationMessages.push(newNameRes.msg); }
        if (valid) {
            params.old_name = oldNameRes.value;
            params.new_name = newNameRes.value.trim();
        }
        return { params, valid, msg: validationMessages.join(' ') };
    }

    function getDropParams(modalEl) {
        let params = {};
        let valid = true;
        let validationMessages = [];
        const colsRes = getRequiredValue('modal-drop-cols', 'Columns', false, true, modalEl);
        if (!colsRes.valid) { valid = false; validationMessages.push(colsRes.msg); }
        else { params.columns_to_drop = colsRes.value; }
        return { params, valid, msg: validationMessages.join(' ') };
    }


    addModalApplyListener(applyFilterBtn, filterModal, filterModalEl, 'filter_rows', getFilterParams);
    addModalApplyListener(applySortBtn, sortModal, sortModalEl, 'sort_values', getSortParams);
    addModalApplyListener(applySplitBtn, splitModal, splitModalEl, 'split_column', getSplitParams);
    addModalApplyListener(applyCombineBtn, combineModal, combineModalEl, 'combine_columns', getCombineParams);
    addModalApplyListener(applyRenameBtn, renameModal, renameModalEl, 'rename_column', getRenameParams);
    if (applyDropBtn && dropModal && dropModalEl) {
        applyDropBtn.addEventListener('click', () => {
            const { params, valid, msg } = getDropParams(dropModalEl);
            if (valid) {
                 if (confirm('Are you sure you want to permanently drop the selected columns?')) {
                    performAction('/clean_operation', 'POST', { operation: 'drop_columns', params: params }, dropModal);
                }
            } else if (msg) {
                displayToast(msg, 'warning');
            }
        });
    } else {
        if (!applyDropBtn) console.warn("Button for action 'drop_columns' not found.");
        if (!dropModalEl) console.warn("Modal element 'dropModalEl' not found.");
    }


    if (sidebar) {
        sidebar.addEventListener('click', handleSidebarClick);
    }
    if (undoBtn) undoBtn.addEventListener('click', () => performAction('/undo', 'POST'));
    if (redoBtn) redoBtn.addEventListener('click', () => performAction('/redo', 'POST'));
    if (saveBtn) {
        saveBtn.addEventListener('click', () => {
            const filename = saveFilenameInput ? saveFilenameInput.value.trim() : '';
            performAction('/save', 'POST', filename ? { filename } : {});
        });
    }
    if (optimizeCategoriesBtn) {
         optimizeCategoriesBtn.addEventListener('click', () => {
            if (confirm("Convert low-cardinality text columns to Category type for memory efficiency? (This action can be undone)")) {
                performAction('/optimize_categories', 'POST');
            }
        });
    }

    const fillMissingMethodSelect = document.getElementById('fill-missing-method');
    if (fillMissingMethodSelect) {
        fillMissingMethodSelect.addEventListener('change', toggleFillValueInput);
    }


    [filterModalEl, sortModalEl, splitModalEl, combineModalEl, renameModalEl, dropModalEl].forEach(modalElInstance => {
        if (modalElInstance) {
            modalElInstance.addEventListener('shown.bs.modal', () => {
                const firstInput = modalElInstance.querySelector('input:not([type=hidden]):not([disabled]), select:not([disabled]), textarea:not([disabled])');
                if (firstInput) {
                    firstInput.focus();
                }
            });
        }
    });

    function updateInitialCounts() {
        if (rowCountSpan && rowCountSpan.textContent.includes('N/A') && tableContainer) {
            const initialRows = tableContainer.querySelectorAll('tbody > tr');
            rowCountSpan.textContent = `Rows: ${initialRows ? initialRows.length : 0}`;
        }
         if (colCountSpan && colCountSpan.textContent.includes('N/A') && tableContainer) {
            const firstRowThs = tableContainer.querySelectorAll('thead > tr > th');
            let colNum = 0;
            if (firstRowThs) {
                firstRowThs.forEach(th => {
                    if (th.textContent.trim() !== '#') {
                        colNum++;
                    }
                });
            }
            colCountSpan.textContent = `Columns: ${colNum}`;
        }
    }

    updateInitialCounts();
    toggleFillValueInput();
    toggleOutlierMethodControls();
    loadAutoCleanConfigToForm();
}); // End DOMContentLoaded