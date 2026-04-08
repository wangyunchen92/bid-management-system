import { create } from 'zustand';
import { getDictByCode } from '@/services/system';

interface DictStoreState {
  cache: Record<string, DictItem[]>;
  loading: Record<string, boolean>;
  getDictItems: (code: string) => Promise<DictItem[]>;
  clearCache: () => void;
}

const useDictStore = create<DictStoreState>((set, get) => ({
  cache: {},
  loading: {},

  getDictItems: async (code: string) => {
    const { cache, loading } = get();
    if (cache[code]) return cache[code];
    if (loading[code]) return [];

    set((state) => ({ loading: { ...state.loading, [code]: true } }));
    try {
      const res = await getDictByCode(code);
      const items = res.data;
      set((state) => ({
        cache: { ...state.cache, [code]: items },
        loading: { ...state.loading, [code]: false },
      }));
      return items;
    } catch {
      set((state) => ({ loading: { ...state.loading, [code]: false } }));
      return [];
    }
  },

  clearCache: () => set({ cache: {}, loading: {} }),
}));

export default useDictStore;
