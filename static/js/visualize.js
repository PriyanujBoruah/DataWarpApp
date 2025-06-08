// static/js/visualize.js

console.log("visualize.js loaded and running!"); // Initial check

document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded and parsed for visualize.js");

    const autoVisualizeBtn = document.getElementById('auto-visualize-btn');
    const autoPlotsContainer = document.getElementById('auto-plots-container');
    const customPlotsContainer = document.getElementById('custom-plots-container');
    const initialMessage = document.getElementById('initial-message');
    const globalMessageContainer = document.getElementById('global-message-container');

    const plotTypeSelect = document.getElementById('plot-type-select');
    const xColumnSelect = document.getElementById('x-column-select');
    const yColumnSelect = document.getElementById('y-column-select');
    const yColumnControlsGroup = document.getElementById('y-column-controls-group');
    const generateIndividualPlotBtn = document.getElementById('generate-individual-plot-btn');
    
    let plotlyJsLoaded = false; // Track if Plotly.js has been loaded via an auto-plot
    let customPlotCounter = 0;

    function displayGlobalMessage(message, type = 'danger') {
        console.log(`Displaying global message (type: ${type}):`, message); // Log message display
        globalMessageContainer.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
              <i class="bi ${type === 'danger' ? 'bi-exclamation-triangle-fill' : 'bi-info-circle-fill'} me-2"></i>
              ${message}
              <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>`;
    }

    function clearGlobalMessage() {
        globalMessageContainer.innerHTML = '';
    }

    if (autoVisualizeBtn) {
        console.log("Auto-visualize button FOUND.");
        autoVisualizeBtn.addEventListener('click', async function() {
            console.log("Auto-visualize button CLICKED!");

            if (initialMessage) initialMessage.style.display = 'none';
            clearGlobalMessage();
            autoPlotsContainer.innerHTML = `<div class="text-center my-5"><div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;"></div><p class="mt-2">Generating automatic visualizations...</p></div>`;
            
            try {
                console.log("Fetching /get_automatic_plots...");
                const response = await fetch("/get_automatic_plots"); // Assumes Flask is at root. Use url_for if needed.
                console.log("Fetch response object:", response);
                console.log("Response status:", response.status);
                console.log("Response ok:", response.ok);

                if (!response.ok) {
                    const errorText = await response.text(); // Get raw text for non-JSON error
                    console.error("Server responded with an error during fetch:", response.status, errorText);
                    displayGlobalMessage(`Server error ${response.status}: ${errorText || 'Failed to fetch plot data.'}`);
                    autoPlotsContainer.innerHTML = ''; // Clear loading
                    return;
                }

                const data = await response.json();
                console.log("Received data from server (parsed JSON):", JSON.parse(JSON.stringify(data))); // Deep copy for logging

                autoPlotsContainer.innerHTML = ''; // Clear loading message

                if (data.error) {
                    console.error("Data contains error property:", data.error);
                    displayGlobalMessage(data.error);
                    return;
                }
                if (data.info) { // For cases where no plots are applicable
                    console.log("Data contains info property:", data.info);
                    autoPlotsContainer.innerHTML = `<div class="alert alert-info">${data.info}</div>`;
                    return;
                }

                if (Object.keys(data).length === 0) {
                    console.log("Received empty data object from server.");
                    autoPlotsContainer.innerHTML = '<div class="alert alert-info">No automatic visualizations were generated. The dataset might not have suitable columns or is empty.</div>';
                    return;
                }
                
                let firstPlotHtmlContentForJsCheck = null; // To check if any plot actually has content for Plotly.js

                for (const groupKey in data) {
                    console.log(`Processing group: ${groupKey}`);
                    const groupData = data[groupKey];
                    if (!groupData || ((!groupData.plots || groupData.plots.length === 0) && (!groupData.messages || groupData.messages.length === 0))) {
                        console.log(`Skipping empty group: ${groupKey}`);
                        continue;
                    }

                    const card = document.createElement('div');
                    card.className = 'card mb-4';
                    
                    const cardHeader = document.createElement('div');
                    cardHeader.className = 'card-header bottom-color-border';
                    cardHeader.textContent = groupData.title || groupKey.charAt(0).toUpperCase() + groupKey.slice(1);
                    card.appendChild(cardHeader);

                    const cardBody = document.createElement('div');
                    cardBody.className = 'card-body';

                    if (groupData.messages && groupData.messages.length > 0) {
                        const messagesDiv = document.createElement('div');
                        messagesDiv.className = 'plot-messages text-muted';
                        groupData.messages.forEach(msgHtml => {
                            const p = document.createElement('div'); // Use div to allow alert HTML
                            p.innerHTML = msgHtml; // msgHtml is already HTML string
                            messagesDiv.appendChild(p);
                        });
                        cardBody.appendChild(messagesDiv);
                        if (groupData.plots && groupData.plots.length > 0) {
                            cardBody.appendChild(document.createElement('hr'));
                        }
                    }

                    if (groupData.plots && groupData.plots.length > 0) {
                        const plotRow = document.createElement('div');
                        if (groupKey === 'correlation') {
                            plotRow.className = 'row'; // Full width for correlation
                            const plotCol = document.createElement('div');
                            plotCol.className = 'col-12';
                            plotCol.id = 'correlation-plot-container'; // For specific styling if needed
                            const plotItem = document.createElement('div');
                            plotItem.className = 'plot-item';
                            plotItem.innerHTML = groupData.plots[0]; // Assuming one correlation plot
                            if (groupData.plots[0] && groupData.plots[0].trim() && !firstPlotHtmlContentForJsCheck) {
                                firstPlotHtmlContentForJsCheck = groupData.plots[0];
                            }
                            plotCol.appendChild(plotItem);
                            plotRow.appendChild(plotCol);
                        } else {
                            // Responsive grid for other plots
                            plotRow.className = 'row row-cols-1 row-cols-lg-2 row-cols-xl-2 g-3 align-items-center';
                            groupData.plots.forEach(plotHtml => {
                                if (plotHtml && plotHtml.trim()) { // Only create elements if plotHtml is not empty
                                    const plotCol = document.createElement('div');
                                    plotCol.className = 'col';
                                    const plotItem = document.createElement('div');
                                    plotItem.className = 'plot-item border rounded';
                                    plotItem.innerHTML = plotHtml;
                                    if (!firstPlotHtmlContentForJsCheck) { // Check first non-empty plot
                                        firstPlotHtmlContentForJsCheck = plotHtml;
                                    }
                                    plotCol.appendChild(plotItem);
                                    plotRow.appendChild(plotCol);
                                } else {
                                    console.warn(`Empty plot HTML found in group ${groupKey}`);
                                }
                            });
                        }
                        if (plotRow.hasChildNodes()) { // Only append row if it actually got plots
                           cardBody.appendChild(plotRow);
                        }
                    } else if ((!groupData.messages || groupData.messages.length === 0) && (!groupData.plots || groupData.plots.length === 0)) {
                        // This case should be caught by the earlier check, but as a fallback:
                        const noVizP = document.createElement('p');
                        noVizP.className = 'text-muted mb-0';
                        noVizP.textContent = 'No visualizations generated for this category.';
                        cardBody.appendChild(noVizP);
                    }
                    
                    card.appendChild(cardBody);
                    autoPlotsContainer.appendChild(card);
                }
                // Check if any plot HTML actually included Plotly.js
                if (firstPlotHtmlContentForJsCheck && firstPlotHtmlContentForJsCheck.includes("plotly.cdn.plot.ly") ) {
                    plotlyJsLoaded = true;
                    console.log("Plotly.js detected as loaded from an auto-plot.");
                } else {
                    console.log("Plotly.js not detected in the first auto-plot HTML. Will be included with first custom plot if needed.");
                }

            } catch (error) {
                console.error('Error in autoVisualizeBtn click handler (outer catch):', error);
                displayGlobalMessage(`Client-side error: ${error.message || 'Unknown error during visualization.'}`);
                autoPlotsContainer.innerHTML = ''; // Clear loading on error
            }
        });
    } else {
        console.error("Auto-visualize button (autoVisualizeBtn) NOT FOUND in the DOM!");
    }

    // --- Individual Plot Generation ---
    function populateSelect(selectElement, optionsArray, defaultOptionText = "-- Select --", useValueAsText = true) {
        if (!selectElement) {
            console.error("populateSelect: selectElement is null or undefined for defaultOptionText:", defaultOptionText);
            return;
        }
        selectElement.innerHTML = `<option value="">${defaultOptionText}</option>`;
        if (optionsArray && Array.isArray(optionsArray)) {
            optionsArray.forEach(opt => {
                const option = document.createElement('option');
                option.value = opt; // Assuming optionsArray is an array of strings
                option.textContent = opt;
                selectElement.appendChild(option);
            });
        } else {
            console.warn("populateSelect: optionsArray is null, undefined, or not an array for:", defaultOptionText, optionsArray);
        }
    }
    
    // Initial population of X-axis (all relevant columns)
    // These constants (ALL_COLUMNS etc.) must be defined in <script> tags in visualize.html
    if (typeof ALL_COLUMNS !== 'undefined') {
        populateSelect(xColumnSelect, ALL_COLUMNS, '-- Select X-Axis --');
    } else {
        console.error("ALL_COLUMNS is not defined. Check <script> tag in HTML.");
    }


    if (plotTypeSelect) {
        plotTypeSelect.addEventListener('change', function() {
            const plotType = this.value;
            console.log("Plot type changed to:", plotType);

            // Ensure column select elements exist before trying to populate
            if (!xColumnSelect || !yColumnSelect || !yColumnControlsGroup) {
                console.error("One or more column select elements are missing for individual plots.");
                return;
            }

            yColumnControlsGroup.style.display = 'none'; // Hide Y by default
            yColumnSelect.value = ''; // Reset Y
            xColumnSelect.value = ''; // Reset X to force re-selection based on new options

            // Check if plot-specific column arrays are defined
            const numCols = typeof PLOT_NUMERIC_COLUMNS !== 'undefined' ? PLOT_NUMERIC_COLUMNS : [];
            const catCols = typeof PLOT_CATEGORICAL_COLUMNS !== 'undefined' ? PLOT_CATEGORICAL_COLUMNS : [];
            const boolCols = typeof BOOLEAN_COLUMNS !== 'undefined' ? BOOLEAN_COLUMNS : [];
            const allCols = typeof ALL_COLUMNS !== 'undefined' ? ALL_COLUMNS : [];

            switch(plotType) {
                case 'histogram':
                    populateSelect(xColumnSelect, numCols, '-- Select Numeric Column --');
                    break;
                case 'countplot':
                    populateSelect(xColumnSelect, [...new Set([...catCols, ...boolCols])], '-- Select Categorical/Bool Column --');
                    break;
                case 'scatter':
                    populateSelect(xColumnSelect, numCols, '-- Select Numeric X --');
                    populateSelect(yColumnSelect, numCols, '-- Select Numeric Y --');
                    yColumnControlsGroup.style.display = 'block';
                    break;
                case 'boxplot':
                    populateSelect(xColumnSelect, [...new Set([...catCols, ...boolCols])], '-- Select Cat./Bool X --');
                    populateSelect(yColumnSelect, numCols, '-- Select Numeric Y --');
                    yColumnControlsGroup.style.display = 'block';
                    break;
                default:
                    populateSelect(xColumnSelect, allCols, '-- Select X-Axis --'); // Fallback
            }
        });
    } else {
        console.error("plotTypeSelect element NOT FOUND.");
    }

    if (generateIndividualPlotBtn) {
        generateIndividualPlotBtn.addEventListener('click', async function() {
            console.log("Generate individual plot button CLICKED!");
            if (initialMessage) initialMessage.style.display = 'none';
            clearGlobalMessage();

            const plotType = plotTypeSelect.value;
            const xCol = xColumnSelect.value;
            const yCol = (yColumnControlsGroup.style.display === 'block') ? yColumnSelect.value : null;

            if (!plotType) { displayGlobalMessage("Please select a plot type."); return; }
            if (!xCol) { displayGlobalMessage("Please select an X-axis column."); return; }
            if ((plotType === 'scatter' || plotType === 'boxplot') && !yCol) {
                displayGlobalMessage("Please select a Y-axis column for this plot type."); return;
            }

            const formData = new FormData();
            formData.append('plot_type', plotType);
            formData.append('x_col', xCol);
            if (yCol) formData.append('y_col', yCol);
            formData.append('include_js', String(!plotlyJsLoaded)); // Request JS if not loaded by auto-plots

            console.log("Form data for custom plot:", { plot_type: plotType, x_col: xCol, y_col: yCol, include_js: !plotlyJsLoaded });


            let customPlotsCard = document.getElementById('custom-visualizations-card');
            if (!customPlotsCard) {
                customPlotsContainer.innerHTML = ''; // Clear any "no custom plots" message
                customPlotsCard = document.createElement('div');
                customPlotsCard.id = 'custom-visualizations-card';
                customPlotsCard.className = 'card mt-4';
                const cardHeader = document.createElement('div');
                cardHeader.className = 'card-header bottom-color-border';
                cardHeader.textContent = 'Custom Visualizations';
                customPlotsCard.appendChild(cardHeader);
                const cardBody = document.createElement('div');
                cardBody.id = 'custom-visualizations-card-body';
                cardBody.className = 'card-body'; // Will hold individual plot items
                customPlotsCard.appendChild(cardBody);
                customPlotsContainer.appendChild(customPlotsCard);
            }
            const customPlotsCardBody = document.getElementById('custom-visualizations-card-body');
            
            const loadingPlotId = `custom-plot-loading-${customPlotCounter}`;
            customPlotsCardBody.insertAdjacentHTML('beforeend', `<div id="${loadingPlotId}" class="plot-item border rounded mb-3 p-3 text-center"><div class="spinner-border text-success spinner-border-sm me-2"></div> Generating ${plotType} for ${xCol}...</div>`);

            try {
                console.log("Fetching /generate_custom_plot...");
                const response = await fetch("/generate_custom_plot", { // Assumes Flask root
                    method: 'POST',
                    body: formData
                });
                console.log("Custom plot fetch response object:", response);
                
                const loadingElement = document.getElementById(loadingPlotId);
                if (loadingElement) loadingElement.remove();

                if (!response.ok) {
                    const errorText = await response.text();
                    console.error("Server responded with an error for custom plot:", response.status, errorText);
                    throw new Error(JSON.parse(errorText).error || `Server error ${response.status}: ${errorText}`);
                }
                
                const result = await response.json();
                console.log("Received custom plot result (parsed JSON):", result);

                if (result.error) {
                    console.error("Custom plot result contains error:", result.error);
                    throw new Error(result.error);
                }
                
                if (result.plot_html) {
                    const plotWrapper = document.createElement('div');
                    plotWrapper.className = 'plot-item border rounded mb-3'; // Each plot in its own wrapper
                    plotWrapper.innerHTML = result.plot_html;
                    customPlotsCardBody.appendChild(plotWrapper);
                    
                    if (result.included_js && result.plot_html.includes("plotly.cdn.plot.ly")) {
                        plotlyJsLoaded = true; // Mark Plotly.js as loaded by this custom plot
                        console.log("Plotly.js loaded via custom plot.");
                    }
                    customPlotCounter++;
                } else {
                    console.warn("Custom plot result did not contain plot_html.");
                    displayGlobalMessage("Failed to retrieve plot HTML from server.", "warning");
                }

            } catch (error) {
                console.error('Error generating/displaying individual plot:', error);
                const loadingElementOnError = document.getElementById(loadingPlotId);
                if (loadingElementOnError) loadingElementOnError.remove();
                
                const errorDiv = document.createElement('div');
                errorDiv.className = 'alert alert-warning alert-sm p-2 mb-3';
                errorDiv.innerHTML = `<strong>Error:</strong> Could not generate plot for <i>${xCol || 'selected column'}</i>. ${error.message || 'Unknown error'}`;
                if (customPlotsCardBody) {
                    customPlotsCardBody.appendChild(errorDiv);
                } else { // Fallback if card body wasn't created
                    displayGlobalMessage(`<strong>Error:</strong> Could not generate plot for <i>${xCol || 'selected column'}</i>. ${error.message || 'Unknown error'}`);
                }
            }
        });
    } else {
        console.error("generateIndividualPlotBtn element NOT FOUND.");
    }
});