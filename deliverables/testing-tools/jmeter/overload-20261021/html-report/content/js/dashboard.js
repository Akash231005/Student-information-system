/*
   Licensed to the Apache Software Foundation (ASF) under one or more
   contributor license agreements.  See the NOTICE file distributed with
   this work for additional information regarding copyright ownership.
   The ASF licenses this file to You under the Apache License, Version 2.0
   (the "License"); you may not use this file except in compliance with
   the License.  You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/
var showControllersOnly = false;
var seriesFilter = "";
var filtersOnlySampleSeries = true;

/*
 * Add header in statistics table to group metrics by category
 * format
 *
 */
function summaryTableHeader(header) {
    var newRow = header.insertRow(-1);
    newRow.className = "tablesorter-no-sort";
    var cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 1;
    cell.innerHTML = "Requests";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 3;
    cell.innerHTML = "Executions";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 7;
    cell.innerHTML = "Response Times (ms)";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 1;
    cell.innerHTML = "Throughput";
    newRow.appendChild(cell);

    cell = document.createElement('th');
    cell.setAttribute("data-sorter", false);
    cell.colSpan = 2;
    cell.innerHTML = "Network (KB/sec)";
    newRow.appendChild(cell);
}

/*
 * Populates the table identified by id parameter with the specified data and
 * format
 *
 */
function createTable(table, info, formatter, defaultSorts, seriesIndex, headerCreator) {
    var tableRef = table[0];

    // Create header and populate it with data.titles array
    var header = tableRef.createTHead();

    // Call callback is available
    if(headerCreator) {
        headerCreator(header);
    }

    var newRow = header.insertRow(-1);
    for (var index = 0; index < info.titles.length; index++) {
        var cell = document.createElement('th');
        cell.innerHTML = info.titles[index];
        newRow.appendChild(cell);
    }

    var tBody;

    // Create overall body if defined
    if(info.overall){
        tBody = document.createElement('tbody');
        tBody.className = "tablesorter-no-sort";
        tableRef.appendChild(tBody);
        var newRow = tBody.insertRow(-1);
        var data = info.overall.data;
        for(var index=0;index < data.length; index++){
            var cell = newRow.insertCell(-1);
            cell.innerHTML = formatter ? formatter(index, data[index]): data[index];
        }
    }

    // Create regular body
    tBody = document.createElement('tbody');
    tableRef.appendChild(tBody);

    var regexp;
    if(seriesFilter) {
        regexp = new RegExp(seriesFilter, 'i');
    }
    // Populate body with data.items array
    for(var index=0; index < info.items.length; index++){
        var item = info.items[index];
        if((!regexp || filtersOnlySampleSeries && !info.supportsControllersDiscrimination || regexp.test(item.data[seriesIndex]))
                &&
                (!showControllersOnly || !info.supportsControllersDiscrimination || item.isController)){
            if(item.data.length > 0) {
                var newRow = tBody.insertRow(-1);
                for(var col=0; col < item.data.length; col++){
                    var cell = newRow.insertCell(-1);
                    cell.innerHTML = formatter ? formatter(col, item.data[col]) : item.data[col];
                }
            }
        }
    }

    // Add support of columns sort
    table.tablesorter({sortList : defaultSorts});
}

$(document).ready(function() {

    // Customize table sorter default options
    $.extend( $.tablesorter.defaults, {
        theme: 'blue',
        cssInfoBlock: "tablesorter-no-sort",
        widthFixed: true,
        widgets: ['zebra']
    });

    var data = {"OkPercent": 16.13364741246008, "KoPercent": 83.86635258753992};
    var dataset = [
        {
            "label" : "FAIL",
            "data" : data.KoPercent,
            "color" : "#FF6347"
        },
        {
            "label" : "PASS",
            "data" : data.OkPercent,
            "color" : "#9ACD32"
        }];
    $.plot($("#flot-requests-summary"), dataset, {
        series : {
            pie : {
                show : true,
                radius : 1,
                label : {
                    show : true,
                    radius : 3 / 4,
                    formatter : function(label, series) {
                        return '<div style="font-size:8pt;text-align:center;padding:2px;color:white;">'
                            + label
                            + '<br/>'
                            + Math.round10(series.percent, -2)
                            + '%</div>';
                    },
                    background : {
                        opacity : 0.5,
                        color : '#000'
                    }
                }
            }
        },
        legend : {
            show : true
        }
    });

    // Creates APDEX table
    createTable($("#apdexTable"), {"supportsControllersDiscrimination": true, "overall": {"data": [0.16133647412460078, 500, 1500, "Total"], "isController": false}, "titles": ["Apdex", "T (Toleration threshold)", "F (Frustration threshold)", "Label"], "items": [{"data": [0.03217320922703359, 500, 1500, "Autocomplete"], "isController": false}, {"data": [0.032169954476479516, 500, 1500, "Offering list"], "isController": false}, {"data": [1.0, 500, 1500, "Health"], "isController": false}, {"data": [0.009612465850450268, 500, 1500, "Component metrics"], "isController": false}, {"data": [0.00900536274410604, 500, 1500, "Consistent hash ring"], "isController": false}, {"data": [0.032163446950541116, 500, 1500, "Course search"], "isController": false}, {"data": [0.013558636041687746, 500, 1500, "ID generator batch"], "isController": false}]}, function(index, item){
        switch(index){
            case 0:
                item = item.toFixed(3);
                break;
            case 1:
            case 2:
                item = formatDuration(item);
                break;
        }
        return item;
    }, [[0, 0]], 3);

    // Create statistics table
    createTable($("#statisticsTable"), {"supportsControllersDiscrimination": true, "overall": {"data": ["Total", 69197, 58033, 83.86635258753992, 2.7144384872176643, 0, 308, 1.0, 9.0, 11.0, 17.0, 3474.791603896756, 669.7114977214522, 555.5342072474139], "isController": false}, "titles": ["Label", "#Samples", "FAIL", "Error %", "Average", "Min", "Max", "Median", "90th pct", "95th pct", "99th pct", "Transactions/s", "Received", "Sent"], "items": [{"data": ["Autocomplete", 9884, 9566, 96.78267907729663, 1.5472480777013409, 0, 53, 1.0, 2.0, 3.0, 12.0, 497.9345088161209, 91.05788531171284, 83.15117285894206], "isController": false}, {"data": ["Offering list", 9885, 9567, 96.78300455235205, 2.062013151239254, 0, 308, 1.0, 2.0, 3.0, 21.0, 497.8594812389826, 122.54460069881641, 79.24911664253337], "isController": false}, {"data": ["Health", 9892, 0, 0.0, 10.063586736757001, 1, 279, 9.0, 13.0, 15.0, 19.0, 496.73596464798635, 74.70443218338856, 73.24915103695892], "isController": false}, {"data": ["Component metrics", 9883, 9788, 99.03875341495497, 1.08519680259031, 0, 56, 1.0, 2.0, 2.0, 6.0, 498.28577190682665, 94.52971381214077, 80.77679505520823], "isController": false}, {"data": ["Consistent hash ring", 9883, 9794, 99.0994637255894, 1.0543357280178145, 0, 12, 1.0, 2.0, 2.0, 4.0, 498.2355313571284, 91.43787652500505, 79.30897618282417], "isController": false}, {"data": ["Course search", 9887, 9569, 96.7836553049459, 2.0143622939213115, 0, 306, 1.0, 2.0, 3.0, 20.0, 497.4841501459193, 102.24177946060179, 78.21772282567677], "isController": false}, {"data": ["ID generator batch", 9883, 9749, 98.64413639583123, 1.1681675604573518, 0, 44, 1.0, 2.0, 2.0, 6.0, 498.1853009375945, 95.15734677449844, 83.1930531839147], "isController": false}]}, function(index, item){
        switch(index){
            // Errors pct
            case 3:
                item = item.toFixed(2) + '%';
                break;
            // Mean
            case 4:
            // Mean
            case 7:
            // Median
            case 8:
            // Percentile 1
            case 9:
            // Percentile 2
            case 10:
            // Percentile 3
            case 11:
            // Throughput
            case 12:
            // Kbytes/s
            case 13:
            // Sent Kbytes/s
                item = item.toFixed(2);
                break;
        }
        return item;
    }, [[0, 0]], 0, summaryTableHeader);

    // Create error table
    createTable($("#errorsTable"), {"supportsControllersDiscrimination": false, "titles": ["Type of error", "Number of errors", "% in errors", "% in all samples"], "items": [{"data": ["429/Too Many Requests", 58033, 100.0, 83.86635258753992], "isController": false}]}, function(index, item){
        switch(index){
            case 2:
            case 3:
                item = item.toFixed(2) + '%';
                break;
        }
        return item;
    }, [[1, 1]]);

        // Create top5 errors by sampler
    createTable($("#top5ErrorsBySamplerTable"), {"supportsControllersDiscrimination": false, "overall": {"data": ["Total", 69197, 58033, "429/Too Many Requests", 58033, "", "", "", "", "", "", "", ""], "isController": false}, "titles": ["Sample", "#Samples", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors", "Error", "#Errors"], "items": [{"data": ["Autocomplete", 9884, 9566, "429/Too Many Requests", 9566, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["Offering list", 9885, 9567, "429/Too Many Requests", 9567, "", "", "", "", "", "", "", ""], "isController": false}, {"data": [], "isController": false}, {"data": ["Component metrics", 9883, 9788, "429/Too Many Requests", 9788, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["Consistent hash ring", 9883, 9794, "429/Too Many Requests", 9794, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["Course search", 9887, 9569, "429/Too Many Requests", 9569, "", "", "", "", "", "", "", ""], "isController": false}, {"data": ["ID generator batch", 9883, 9749, "429/Too Many Requests", 9749, "", "", "", "", "", "", "", ""], "isController": false}]}, function(index, item){
        return item;
    }, [[0, 0]], 0);

});
