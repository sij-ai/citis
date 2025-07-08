(function() {{
    var overlay = document.getElementById('perma-overlay');
    if (overlay) {{
        var height = overlay.offsetHeight + 'px';
        document.body.style.setProperty('padding-top', height, 'important');
    }}
    // Update favicon
    var favicon = document.querySelector('link[rel*="icon"]');
    if (favicon) {{
        favicon.href = favicon.href;
    }}
}})();

function highlightTextFragment() {{
    var textFragment = '{text_fragment}';
    if (!textFragment) return;
    if (!textFragment.startsWith('#:~:text=')) {{
        textFragment = '#:~:text=' + textFragment;
    }}
    var currentUrl = window.location.href.split('#')[0];
    window.location.replace(currentUrl + textFragment);
    // Manual fallback
    setTimeout(function() {{
        var searchText = '{cleaned_fragment}'.toLowerCase();
        if (!searchText) return;
        function findAndHighlight(searchText) {{
            var found = window.find(searchText, false, false, true, false, true, false);
            if (found) {{
                var selection = window.getSelection();
                if (selection.rangeCount > 0) {{
                    var range = selection.getRangeAt(0);
                    var rect = range.getBoundingClientRect();
                    var overlayHeight = document.getElementById('perma-overlay').offsetHeight;
                    window.scrollTo({{
                        top: rect.top + window.pageYOffset - overlayHeight - 20,
                        behavior: 'smooth'
                    }});
                    var span = document.createElement('span');
                    span.style.backgroundColor = '#b58900';
                    span.style.color = '#002b36';
                    span.style.transition = 'all 0.5s ease';
                    try {{
                        range.surroundContents(span);
                        setTimeout(function() {{
                            span.style.backgroundColor = 'transparent';
                            span.style.color = 'inherit';
                            setTimeout(function() {{
                                var parent = span.parentNode;
                                while (span.firstChild) {{
                                    parent.insertBefore(span.firstChild, span);
                                }}
                                parent.removeChild(span);
                            }}, 500);
                        }}, 3000);
                    }} catch(e) {{
                        // Just scroll if surroundContents fails
                    }}
                }}
            }}
        }}
        findAndHighlight(searchText);
    }}, 100);
}}

// Handle clicks on the fragment container + auto-highlight on load
document.addEventListener('DOMContentLoaded', function() {{
    var fragmentContainer = document.querySelector('.fragment-text-container');
    if (fragmentContainer) {{
        fragmentContainer.addEventListener('click', highlightTextFragment);
        
        // Auto-highlight text fragment on page load if it exists
        var textFragment = '{text_fragment}';
        if (textFragment && textFragment.trim()) {{
            // Small delay to ensure page content is fully rendered
            setTimeout(function() {{
                highlightTextFragment();
            }}, 500);
        }}
    }}
}});

var analyticsData = {analytics_data_json};
var analyticsExpanded = false;

// Configurable colors from server
var styleBackgroundColor = '{style_background_color}';
var styleLinkColor = '{style_link_color}';
var styleAccentColor = '{style_accent_color}';

function copyCiteToClipboard() {{
    try {{
        var pageTitle = document.title;
        var textFragment = '{cleaned_fragment}';
        var currentDate = new Date();
        var month = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][currentDate.getMonth()];
        var formattedDate = month + ' ' + currentDate.getDate() + ', ' + currentDate.getFullYear();
        var currentUrl = window.location.href.split('#')[0]; // Remove any existing fragment
        
        // Add text fragment to URL if it exists
        var urlWithFragment = currentUrl;
        if (textFragment && textFragment.trim()) {{
            var encodedFragment = encodeURIComponent(textFragment);
            urlWithFragment = currentUrl + '#:~:text=' + encodedFragment;
        }}
        
        var citationText = '';
        if (textFragment && textFragment.trim()) {{
            citationText = '"' + textFragment + '" ';
        }}
        
        var tempDiv = document.createElement('div');
        tempDiv.appendChild(document.createTextNode(citationText));
        
        var link = document.createElement('a');
        link.href = urlWithFragment;
        link.textContent = pageTitle;
        tempDiv.appendChild(link);
        
        tempDiv.appendChild(document.createTextNode(' (last accessed ' + formattedDate + ').'));
        
        tempDiv.style.position = 'absolute';
        tempDiv.style.left = '-9999px';
        tempDiv.setAttribute('contenteditable', 'true');
        document.body.appendChild(tempDiv);
        
        var range = document.createRange();
        range.selectNodeContents(tempDiv);
        var selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        
        var copySuccessful = document.execCommand('copy');
        document.body.removeChild(tempDiv);
        
        if (copySuccessful) {{
            showCopySuccessIndicator();
        }} else {{
            alert('Unable to copy to clipboard');
        }}
    }} catch (error) {{
        console.error('Error copying citation:', error);
        alert('Error copying citation: ' + error.message);
    }}
}}

function showCopySuccessIndicator() {{
    var indicator = document.createElement("div");
    indicator.textContent = "📋 Citation copied to clipboard";
    indicator.style.cssText = 'position: fixed; top: 50px; right: 20px; background: #4CAF50; color: white; padding: 10px 20px; border-radius: 5px; z-index: 2147483648; font-family: system-ui, -apple-system, sans-serif; font-size: 14px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); transition: all 0.3s ease;';
    
    document.body.appendChild(indicator);
    
    setTimeout(function() {{
        indicator.style.opacity = "0";
        setTimeout(function() {{ 
            if (indicator.parentNode) {{
                indicator.parentNode.removeChild(indicator); 
            }}
        }}, 300);
    }}, 3000);
}}

function toggleAnalytics() {{
    var section = document.getElementById('analytics-section');
    var overlay = document.getElementById('perma-overlay');
    if (!section || !overlay) return;
    analyticsExpanded = !analyticsExpanded;
    if (analyticsExpanded) {{
        // Position the analytics section right below the main overlay
        var overlayHeight = overlay.offsetHeight;
        section.style.top = overlayHeight + 'px';
        section.style.display = 'block';
        setTimeout(function() {{
            section.classList.add('active');
            // Update body padding to account for both overlay and analytics
            var totalHeight = overlay.offsetHeight + section.offsetHeight + 'px';
            document.body.style.setProperty('padding-top', totalHeight, 'important');
        }}, 10);
        renderAnalytics(analyticsData);
    }} else {{
        section.classList.remove('active');
        setTimeout(function() {{
            section.style.display = 'none';
            // Reset body padding to just the overlay height
            var height = overlay.offsetHeight + 'px';
            document.body.style.setProperty('padding-top', height, 'important');
        }}, 300);
    }}
}}

function renderAnalytics(data) {{
    renderLineChart(data.visits);
    renderPieChart(data.visits);
}}

function renderLineChart(visits) {{
    var chart = document.getElementById('visits-chart');
    if (!chart) return;
    
    if (!visits || visits.length === 0) {{
        chart.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #586e75;">No visit data</div>';
        return;
    }}

    // Group visits by date
    var visitsByDate = {{}};
    var dateFormat = new Intl.DateTimeFormat('en-US');
    
    visits.forEach(function(visit) {{
        var visitDate = new Date(visit.visited_at);
        var dateKey = visitDate.toISOString().split('T')[0]; // YYYY-MM-DD format
        visitsByDate[dateKey] = (visitsByDate[dateKey] || 0) + 1;
    }});

    var sortedDates = Object.keys(visitsByDate).sort();
    
    if (sortedDates.length === 0) {{
        chart.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #586e75;">No valid visit data</div>';
        return;
    }}

    if (sortedDates.length === 1) {{
        var visitCount = visitsByDate[sortedDates[0]];
        var displayDate = new Date(sortedDates[0]).toLocaleDateString();
        chart.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: ' + styleAccentColor + '; flex-direction: column; text-align: center;">' +
            '<div style="font-size: 24px; font-weight: bold; margin-bottom: 4px;">' + visitCount + '</div>' +
            '<div style="font-size: 10px; color: #586e75;">visits on</div>' +
            '<div style="font-size: 11px; color: #93a1a1;">' + displayDate + '</div>' +
            '</div>';
        return;
    }}

    // Fill in missing dates for smoother chart
    var startDate = new Date(sortedDates[0]);
    var endDate = new Date(sortedDates[sortedDates.length - 1]);
    var dayDiff = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24));
    
    // If more than 90 days, group by week instead of day
    var useWeekly = dayDiff > 90;
    var finalData = {{}};
    
    if (useWeekly) {{
        // Group by week
        Object.keys(visitsByDate).forEach(function(dateKey) {{
            var date = new Date(dateKey);
            var weekStart = new Date(date);
            weekStart.setDate(date.getDate() - date.getDay()); // Start of week (Sunday)
            var weekKey = weekStart.toISOString().split('T')[0];
            finalData[weekKey] = (finalData[weekKey] || 0) + visitsByDate[dateKey];
        }});
    }} else {{
        finalData = visitsByDate;
    }}

    var finalDates = Object.keys(finalData).sort();
    var maxVisits = Math.max.apply(Math, Object.values(finalData));

    var chartWidth = 280;
    var chartHeight = 60;
    var padding = 10;

    if (maxVisits === 0) {{
        chart.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #586e75;">No visits found</div>';
        return;
    }}

    var svg = '<svg width="' + chartWidth + '" height="' + chartHeight + '" viewBox="0 0 ' + chartWidth + ' ' + chartHeight + '">';
    
    // Grid lines
    for (var i = 0; i <= 4; i++) {{
        var y = padding + (i / 4) * (chartHeight - 2 * padding);
        svg += '<line x1="' + padding + '" y1="' + y + '" x2="' + (chartWidth - padding) + '" y2="' + y + '" stroke="#073642" stroke-width="1" opacity="0.3"/>';
    }}

    // Plot points
    var points = [];
    finalDates.forEach(function(date, index) {{
        var x = padding + (index / Math.max(1, finalDates.length - 1)) * (chartWidth - 2 * padding);
        var visitCount = finalData[date] || 0;
        var y = (chartHeight - padding) - ((visitCount / maxVisits) * (chartHeight - 2 * padding));
        points.push([x, y, visitCount]);
    }});

    // Draw area under curve
    if (points.length >= 2) {{
        var areaPath = 'M' + points[0][0] + ',' + (chartHeight - padding);
        points.forEach(function(point) {{
            areaPath += ' L' + point[0] + ',' + point[1];
        }});
        areaPath += ' L' + points[points.length - 1][0] + ',' + (chartHeight - padding) + ' Z';
        svg += '<path d="' + areaPath + '" fill="' + styleAccentColor + '" opacity="0.1"/>';
    }}

    // Draw line
    if (points.length >= 2) {{
        var linePath = 'M' + points[0][0] + ',' + points[0][1];
        for (var i = 1; i < points.length; i++) {{
            linePath += ' L' + points[i][0] + ',' + points[i][1];
        }}
        svg += '<path d="' + linePath + '" fill="none" stroke="' + styleAccentColor + '" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>';
    }}

    // Draw points with hover info
    points.forEach(function(point, index) {{
        var date = finalDates[index];
        var displayDate = new Date(date).toLocaleDateString();
        var visitCount = point[2];
                    svg += '<circle cx="' + point[0] + '" cy="' + point[1] + '" r="3" fill="' + styleAccentColor + '" stroke="' + styleBackgroundColor + '" stroke-width="1">';
        svg += '<title>' + displayDate + ': ' + visitCount + ' visit' + (visitCount !== 1 ? 's' : '') + '</title>';
        svg += '</circle>';
    }});

    // Y-axis labels
    for (var i = 0; i <= 2; i++) {{
        var labelValue = Math.round((maxVisits * (2 - i)) / 2);
        var y = padding + (i / 2) * (chartHeight - 2 * padding);
        svg += '<text x="' + (padding - 2) + '" y="' + (y + 3) + '" font-family="monospace" font-size="8" fill="#586e75" text-anchor="end">' + labelValue + '</text>';
    }}

    svg += '</svg>';
    
    var timeUnit = useWeekly ? 'weeks' : 'days';
    chart.innerHTML = svg + '<div style="text-align: center; font-size: 9px; color: #586e75; margin-top: 2px;">Time unit: ' + timeUnit + '</div>';
}}

function renderPieChart(visits) {{
    var countryList = document.getElementById('country-list');
    if (!countryList) return;
    var countries = {{}};
    visits.forEach(function(visit) {{
        if (visit.country) {{
            countries[visit.country] = (countries[visit.country] || 0) + 1;
        }}
    }});
    var sortedCountries = Object.keys(countries).map(function(country) {{
        return [country, countries[country]];
    }}).sort(function(a, b) {{
        return b[1] - a[1];
    }}).slice(0, 6);
    if (sortedCountries.length === 0) {{
        countryList.innerHTML = '<div style="color: #586e75;">No country data</div>';
        return;
    }}
    var totalVisits = sortedCountries.reduce(function(sum, item) {{ return sum + item[1]; }}, 0);
    var radius = 35;
    var centerX = 40;
    var centerY = 40;
    var colors = ['rgb(255, 225, 0)', 'rgb(255, 200, 0)', 'rgb(255, 175, 0)', 'rgb(255, 150, 0)', 'rgb(255, 125, 0)', 'rgb(255, 100, 0)'];
    var svg = '<svg width="80" height="80" viewBox="0 0 80 80">';
    var currentAngle = 0;
    sortedCountries.forEach(function(item, index) {{
        var country = item[0];
        var count = item[1];
        var percentage = (count / totalVisits) * 100;
        var sliceAngle = (count / totalVisits) * 2 * Math.PI;
        var x1 = centerX + radius * Math.cos(currentAngle);
        var y1 = centerY + radius * Math.sin(currentAngle);
        var x2 = centerX + radius * Math.cos(currentAngle + sliceAngle);
        var y2 = centerY + radius * Math.sin(currentAngle + sliceAngle);
        var largeArcFlag = sliceAngle > Math.PI ? 1 : 0;
        var pathData = [
            'M', centerX, centerY,
            'L', x1, y1,
            'A', radius, radius, 0, largeArcFlag, 1, x2, y2,
            'Z'
        ].join(' ');
        svg += '<path d="' + pathData + '" fill="' + colors[index % colors.length] + '"/>';
        currentAngle += sliceAngle;
    }});
    svg += '</svg>';
    var legendHtml = '';
    sortedCountries.forEach(function(item, index) {{
        var country = item[0];
        var count = item[1];
        var percentage = Math.round((count / totalVisits) * 100);
        legendHtml += '<div class="country-item" style="justify-content: flex-start; gap: 8px;">' +
            '<div style="width: 12px; height: 12px; background: ' + colors[index % colors.length] + '; border-radius: 2px; flex-shrink: 0;"></div>' +
            '<span style="flex: 1;">' + country + '</span>' +
            '<span style="color: #93a1a1;">' + count + ' (' + percentage + '%)</span>' +
            '</div>';
    }});
    countryList.innerHTML = '<div style="display: flex; gap: 15px; align-items: flex-start;">' +
        '<div style="flex-shrink: 0;">' + svg + '</div>' +
        '<div style="flex: 1; display: flex; flex-direction: column; gap: 3px;">' + legendHtml + '</div>' +
        '</div>';
}} 