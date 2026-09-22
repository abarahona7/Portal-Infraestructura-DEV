import { useState } from 'react';

export const useModuleModals = () => {
  const [editingItem, setEditingItem] = useState(null);
  const [newItem, setNewItem] = useState(null);

  const [selectedUser, setSelectedUser] = useState(null);

  const [historyEquipo, setHistoryEquipo] = useState(null);
  const [historyUsuario, setHistoryUsuario] = useState(null);
  const [historyAnexo, setHistoryAnexo] = useState(null);
  const [historyPCGenerico, setHistoryPCGenerico] = useState(null);

  return {
    editingItem,
    setEditingItem,

    newItem,
    setNewItem,

    selectedUser,
    setSelectedUser,

    historyEquipo,
    setHistoryEquipo,

    historyUsuario,
    setHistoryUsuario,

    historyAnexo,
    setHistoryAnexo,

    historyPCGenerico,
    setHistoryPCGenerico,
  };
};