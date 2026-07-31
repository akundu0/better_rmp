import { useState, useEffect, useCallback } from "react";
import {
  Search,
  Loader2,
  ChevronLeft,
  ChevronRight,
  ArrowLeftFromLine,
} from "lucide-react";
import { searchProfessors } from "../api";
import type { School, Professor, SearchFilters } from "../api";
import FilterPanel from "./FilterPanel";
import ProfessorCard from "./ProfessorCard";
import ProfessorDetailView from "./ProfessorDetail";

interface Props {
  school: School;
  onChangeSchool: () => void;
}

export default function SearchView({ school, onChangeSchool }: Props) {
  const [filters, setFilters] = useState<SearchFilters>({
    school_id: school.id,
    sort_by: "avg_rating",
    sort_order: "desc",
    limit: 20,
    offset: 0,
  });
  const [nameQuery, setNameQuery] = useState("");
  const [results, setResults] = useState<Professor[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedProfessor, setSelectedProfessor] = useState<string | null>(null);

  const doSearch = useCallback(
    async (f: SearchFilters) => {
      setLoading(true);
      setError("");
      try {
        const res = await searchProfessors(f);
        setResults(res.results);
        setTotal(res.total);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Search failed");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    doSearch(filters);
  }, [filters, doSearch]);

  const handleNameSearch = () => {
    setFilters((prev) => ({ ...prev, q: nameQuery || undefined, offset: 0 }));
  };

  const handleFiltersChange = (newFilters: SearchFilters) => {
    setFilters(newFilters);
  };

  const page = Math.floor((filters.offset || 0) / (filters.limit || 20));
  const totalPages = Math.ceil(total / (filters.limit || 20));

  if (selectedProfessor) {
    return (
      <ProfessorDetailView
        professorId={selectedProfessor}
        onBack={() => setSelectedProfessor(null)}
      />
    );
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="bg-indigo-600 text-white px-4 py-3">
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="text-sm font-bold">Better RMP</h1>
            <p className="text-[11px] text-indigo-200 truncate max-w-[280px]">
              {school.name}
            </p>
          </div>
          <button
            onClick={onChangeSchool}
            className="text-xs text-indigo-200 hover:text-white flex items-center gap-1 transition-colors"
          >
            <ArrowLeftFromLine className="w-3 h-3" />
            Change
          </button>
        </div>

        {/* Search bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-indigo-300" />
          <input
            type="text"
            placeholder="Search by professor name..."
            value={nameQuery}
            onChange={(e) => setNameQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleNameSearch()}
            className="w-full pl-9 pr-16 py-2 text-sm rounded-lg bg-indigo-500/50 text-white placeholder-indigo-300 border border-indigo-400/30 focus:outline-none focus:ring-2 focus:ring-white/30"
          />
          <button
            onClick={handleNameSearch}
            className="absolute right-1.5 top-1/2 -translate-y-1/2 px-2.5 py-1 text-xs font-medium bg-white text-indigo-600 rounded-md hover:bg-indigo-50 transition-colors"
          >
            Search
          </button>
        </div>
      </div>

      {/* Filters */}
      <FilterPanel
        schoolId={school.id}
        filters={filters}
        onFiltersChange={handleFiltersChange}
      />

      {/* Results count */}
      <div className="px-4 py-2 text-xs text-gray-500 border-b border-gray-100 flex items-center justify-between">
        <span>
          {loading ? (
            <span className="flex items-center gap-1">
              <Loader2 className="w-3 h-3 animate-spin" />
              Searching...
            </span>
          ) : (
            `${total} professor${total !== 1 ? "s" : ""} found`
          )}
        </span>
        {totalPages > 1 && (
          <span>
            Page {page + 1} of {totalPages}
          </span>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mt-2 p-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
          {error}
        </div>
      )}

      {/* Results list */}
      <div className="flex-1 overflow-y-auto">
        {!loading && results.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-gray-400">
            <Search className="w-8 h-8 mb-2" />
            <p className="text-sm">No professors match your filters</p>
            <p className="text-xs mt-1">Try adjusting your search criteria</p>
          </div>
        )}
        {results.map((prof) => (
          <ProfessorCard
            key={prof.id}
            professor={prof}
            onClick={() => setSelectedProfessor(prof.id)}
          />
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="border-t border-gray-200 px-4 py-2 flex items-center justify-between">
          <button
            onClick={() =>
              setFilters((prev) => ({
                ...prev,
                offset: Math.max(0, (prev.offset || 0) - (prev.limit || 20)),
              }))
            }
            disabled={page === 0}
            className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 disabled:text-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-4 h-4" /> Prev
          </button>
          <span className="text-xs text-gray-500">
            {page + 1} / {totalPages}
          </span>
          <button
            onClick={() =>
              setFilters((prev) => ({
                ...prev,
                offset: (prev.offset || 0) + (prev.limit || 20),
              }))
            }
            disabled={page >= totalPages - 1}
            className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 disabled:text-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            Next <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
