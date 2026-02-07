export const parseDocx = async (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = function(event) {
      const arrayBuffer = event.target?.result;
      if (!arrayBuffer) {
        reject(new Error("Failed to read file"));
        return;
      }

      // Use window.mammoth to avoid npm install dependency for this demo
      // In a real build environment, we would import mammoth from 'mammoth'
      if (window.mammoth) {
        window.mammoth.extractRawText({ arrayBuffer: arrayBuffer })
          .then((result: any) => resolve(result.value))
          .catch((err: any) => reject(err));
      } else {
        reject(new Error("Mammoth library not loaded"));
      }
    };
    reader.readAsArrayBuffer(file);
  });
};

export const exportToExcel = (data: any[], fileName: string, sheetName: string = "Sheet1") => {
  if (!window.XLSX) {
    alert("Excel export library not loaded.");
    return;
  }
  
  const ws = window.XLSX.utils.json_to_sheet(data);
  const wb = window.XLSX.utils.book_new();
  window.XLSX.utils.book_append_sheet(wb, ws, sheetName);
  window.XLSX.writeFile(wb, `${fileName}.xlsx`);
};

export const copyToClipboard = async (data: any[], columns?: { key: string; header: string }[]): Promise<void> => {
    if (data.length === 0) return;

    // Determine headers and keys
    let keys: string[] = [];
    let headers: string[] = [];

    if (columns) {
        keys = columns.map(c => c.key);
        headers = columns.map(c => c.header);
    } else {
        keys = Object.keys(data[0]);
        headers = keys;
    }

    // 1. Construct Text Format (TSV) for Excel/Sheets (fallback)
    const tsvHeaderRow = headers.join('\t');
    const tsvRows = data.map(row => {
        return keys.map(key => {
            let cell = row[key];
            if (cell === undefined || cell === null) cell = '';
            if (typeof cell === 'string') {
                cell = cell.replace(/\n/g, ' '); // Flatten for TSV
            }
            return cell;
        }).join('\t');
    }).join('\n');
    const textData = `${tsvHeaderRow}\n${tsvRows}`;

    // 2. Construct HTML Format for Feishu Docs/Word
    // Using a full HTML structure with meta charset helps with encoding and structure recognition
    const htmlHeaderRows = headers.map(h => `<th style="border: 1px solid #888; padding: 5px; background-color: #f2f2f2;">${h}</th>`).join('');
    
    const htmlBodyRows = data.map(row => {
        const cells = keys.map(key => {
            let cell = row[key];
            if (cell === undefined || cell === null) cell = '';
            if (typeof cell === 'string') {
                // Preserve newlines for HTML representation
                cell = cell.replace(/\n/g, '<br>');
            }
            return `<td style="border: 1px solid #888; padding: 5px;">${cell}</td>`;
        }).join('');
        return `<tr>${cells}</tr>`;
    }).join('');

    // Wrap in a complete HTML document to ensure Feishu parses it as a rich table
    const htmlData = `
        <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns="http://www.w3.org/TR/REC-html40">
        <head>
            <meta charset="utf-8">
            <style>
                table { border-collapse: collapse; border: 1px solid #888; width: 100%; font-family: sans-serif; }
                td, th { border: 1px solid #888; padding: 5px; text-align: left; vertical-align: top; font-size: 14px; }
            </style>
        </head>
        <body>
            <table>
                <thead><tr>${htmlHeaderRows}</tr></thead>
                <tbody>${htmlBodyRows}</tbody>
            </table>
        </body>
        </html>
    `;

    try {
        if (typeof ClipboardItem !== "undefined") {
            const blobText = new Blob([textData], { type: 'text/plain' });
            const blobHtml = new Blob([htmlData], { type: 'text/html' });
            
            await navigator.clipboard.write([
                new ClipboardItem({
                    'text/plain': blobText,
                    'text/html': blobHtml
                })
            ]);
        } else {
            // Fallback for older browsers or insecure contexts
            await navigator.clipboard.writeText(textData);
        }
    } catch (err) {
        console.warn('ClipboardItem failed, falling back to writeText', err);
        await navigator.clipboard.writeText(textData);
    }
};