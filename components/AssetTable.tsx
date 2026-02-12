/**
 * 通用资产表格组件
 * 支持角色、道具、场景三种资产类型的展示和编辑
 */

import React from 'react';
import { Trash2 } from 'lucide-react';
import { Asset } from '../services/assetService';

interface ColumnConfig {
  key: keyof Asset;
  label: string;
  editable: boolean;
}

interface AssetTableProps {
  assets: Asset[];
  assetType: 'CHARACTER' | 'PROP' | 'SCENE';
  columns: ColumnConfig[];
  editingAssets: Set<number>;
  editedAssets: Map<number, Asset>;
  onEdit: (asset: Asset) => void;
  onSave: (assetId: number) => void;
  onCancel: (assetId: number) => void;
  onDelete: (assetId: number, assetName: string) => void;
  onFieldChange: (assetId: number, field: keyof Asset, value: string) => void;
}

export default function AssetTable({
  assets,
  assetType,
  columns,
  editingAssets,
  editedAssets,
  onEdit,
  onSave,
  onCancel,
  onDelete,
  onFieldChange,
}: AssetTableProps) {
  const getAssetTypeLabel = () => {
    const labels = {
      CHARACTER: '角色',
      PROP: '道具',
      SCENE: '场景',
    };
    return labels[assetType];
  };

  if (assets.length === 0) {
    return null;
  }

  return (
    <div className="mb-8">
      <h3 className="text-lg font-semibold text-gray-900 mb-3">
        {getAssetTypeLabel()} ({assets.length})
      </h3>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase"
                >
                  {column.label}
                </th>
              ))}
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                操作
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {assets.map((asset) => {
              const isEditing = editingAssets.has(asset.id);
              const editedAsset = editedAssets.get(asset.id) || asset;

              return (
                <tr key={asset.id}>
                  {columns.map((column) => (
                    <td key={column.key} className="px-4 py-3 text-sm">
                      {isEditing && column.editable ? (
                        <input
                          type="text"
                          value={(editedAsset[column.key] as string) || ''}
                          onChange={(e) =>
                            onFieldChange(asset.id, column.key, e.target.value)
                          }
                          className="w-full px-2 py-1 border border-gray-300 rounded"
                        />
                      ) : (
                        <span
                          className={
                            column.key === 'name' ? 'text-gray-900' : 'text-gray-600'
                          }
                        >
                          {(asset[column.key] as string) || ''}
                        </span>
                      )}
                    </td>
                  ))}
                  <td className="px-4 py-3 text-sm">
                    {isEditing ? (
                      <div className="flex gap-2">
                        <button
                          onClick={() => onSave(asset.id)}
                          className="text-green-600 hover:text-green-800"
                        >
                          保存
                        </button>
                        <button
                          onClick={() => onCancel(asset.id)}
                          className="text-gray-600 hover:text-gray-800"
                        >
                          取消
                        </button>
                      </div>
                    ) : (
                      <div className="flex gap-2">
                        <button
                          onClick={() => onEdit(asset)}
                          className="text-indigo-600 hover:text-indigo-800"
                        >
                          编辑
                        </button>
                        <button
                          onClick={() => onDelete(asset.id, asset.name)}
                          className="text-red-600 hover:text-red-800"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
