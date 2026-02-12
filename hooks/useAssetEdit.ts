/**
 * 资产编辑状态管理Hook
 * 管理资产的编辑状态、字段变更和保存逻辑
 */

import { useState } from 'react';
import { Asset, assetService } from '../services/assetService';

interface UseAssetEditOptions {
  projectId: number;
  onSaveSuccess?: (asset: Asset) => void;
  onSaveError?: (error: string) => void;
}

export function useAssetEdit({ projectId, onSaveSuccess, onSaveError }: UseAssetEditOptions) {
  const [editingAssets, setEditingAssets] = useState<Set<number>>(new Set());
  const [editedAssets, setEditedAssets] = useState<Map<number, Asset>>(new Map());

  const handleEditAsset = (asset: Asset) => {
    setEditingAssets(prev => new Set(prev).add(asset.id));
    setEditedAssets(prev => new Map(prev).set(asset.id, { ...asset }));
  };

  const handleCancelEdit = (assetId: number) => {
    setEditingAssets(prev => {
      const next = new Set(prev);
      next.delete(assetId);
      return next;
    });
    setEditedAssets(prev => {
      const next = new Map(prev);
      next.delete(assetId);
      return next;
    });
  };

  const handleFieldChange = (assetId: number, field: keyof Asset, value: string) => {
    setEditedAssets(prev => {
      const next = new Map(prev);
      const asset = next.get(assetId);
      if (asset) {
        next.set(assetId, { ...asset, [field]: value });
      }
      return next;
    });
  };

  const handleSaveAsset = async (assetId: number): Promise<Asset | null> => {
    const editedAsset = editedAssets.get(assetId);
    if (!editedAsset) return null;

    try {
      await assetService.updateAsset(projectId, assetId, {
        name: editedAsset.name,
        description: editedAsset.description,
        gender: editedAsset.gender,
        age: editedAsset.age,
        voice: editedAsset.voice,
        role: editedAsset.role,
      });

      handleCancelEdit(assetId);

      if (onSaveSuccess) {
        onSaveSuccess(editedAsset);
      }

      return editedAsset;
    } catch (err: any) {
      const errorMessage = err.message || '保存失败';
      if (onSaveError) {
        onSaveError(errorMessage);
      }
      return null;
    }
  };

  return {
    editingAssets,
    editedAssets,
    handleEditAsset,
    handleCancelEdit,
    handleFieldChange,
    handleSaveAsset,
  };
}
