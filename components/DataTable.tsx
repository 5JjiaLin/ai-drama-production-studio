import React, { useState } from 'react';
import { Copy, Download, Check } from 'lucide-react';
import { exportToExcel, copyToClipboard } from '../services/fileUtils';
import Button from './Button';

interface Column {
  key: string;
  header: string;
  width?: string;
}

interface DataTableProps {
  title: string;
  data: any[];
  columns: Column[];
  filename: string;
}

const DataTable: React.FC<DataTableProps> = ({ title, data, columns, filename }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      // Pass columns so we get the correct Chinese headers in the clipboard data
      await copyToClipboard(data, columns);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      alert('无法复制到剪贴板');
    }
  };

  const handleExport = () => {
    exportToExcel(data, filename);
  };

  if (!data || data.length === 0) return null;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden mb-6">
      <div className="px-6 py-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-50/50">
        <h3 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
          {title}
          <span className="text-xs font-normal text-slate-500 bg-slate-200 px-2 py-0.5 rounded-full">
            {data.length} 项
          </span>
        </h3>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleCopy} className="text-xs h-8">
            {copied ? <Check size={14} className="mr-1.5" /> : <Copy size={14} className="mr-1.5" />}
            {copied ? '已复制' : '复制表格'}
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport} className="text-xs h-8">
            <Download size={14} className="mr-1.5" />
            导出 Excel
          </Button>
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-600">
          <thead className="bg-slate-50 text-xs uppercase text-slate-500 font-semibold border-b border-slate-200">
            <tr>
              {columns.map((col) => (
                <th key={col.key} className={`px-6 py-3 ${col.width || ''}`}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.map((row, idx) => (
              <tr key={idx} className="hover:bg-slate-50 transition-colors">
                {columns.map((col) => (
                  <td key={col.key} className="px-6 py-4 align-top">
                    {row[col.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DataTable;