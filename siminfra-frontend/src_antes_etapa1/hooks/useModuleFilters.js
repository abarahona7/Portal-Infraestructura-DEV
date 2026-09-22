import { useState } from 'react';

export const useModuleFilters = () => {
  const [search, setSearch] = useState('');
  const [selectedDpto, setSelectedDpto] = useState('');
  const [selectedCategoriaEquipo, setSelectedCategoriaEquipo] = useState('');
  const [selectedEstadoIP, setSelectedEstadoIP] = useState('');
  const [selectedEstadoAnexo, setSelectedEstadoAnexo] = useState('');

  const resetFilters = () => {
    setSearch('');
    setSelectedDpto('');
    setSelectedCategoriaEquipo('');
    setSelectedEstadoIP('');
    setSelectedEstadoAnexo('');
  };

  return {
    search,
    setSearch,

    selectedDpto,
    setSelectedDpto,

    selectedCategoriaEquipo,
    setSelectedCategoriaEquipo,

    selectedEstadoIP,
    setSelectedEstadoIP,

    selectedEstadoAnexo,
    setSelectedEstadoAnexo,

    resetFilters,
  };
};