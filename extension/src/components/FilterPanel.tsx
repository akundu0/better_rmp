import { useState, useEffect } from "react";
import { SlidersHorizontal, ChevronDown, ChevronUp } from "lucide-react";
import { getDepartments, getTags } from "../api";
import type { SearchFilters } from "../api";

interface Props {
  schoolId: string;
  filters: SearchFilters;
  onFiltersChange: (filters: SearchFilters) => void;
}

export default function FilterPanel({ schoolId, filters, onFiltersChange }: Props) {
  const [departments, setDepartments] = useState<string[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    getDepartments(schoolId).then(setDepartments).catch(() => {});
    getTags(schoolId).then(setTags).catch(() => {});
  }, [schoolId]);

  const update = (partial: Partial<SearchFilters>) => {
    onFiltersChange({ ...filters, ...partial, offset: 0 });
  };

  return (
    <div className="border-b border-gray-200 bg-gray-50">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors"
      >
        <span className="flex items-center gap-1.5">
          <SlidersHorizontal className="w-3.5 h-3.5" />
          Filters
        </span>
        {expanded ? (
          <ChevronUp className="w-4 h-4" />
        ) : (
          <ChevronDown className="w-4 h-4" />
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-3 space-y-3">
          {/* Department */}
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Department
            </label>
            <select
              value={filters.department || ""}
              onChange={(e) => update({ department: e.target.value || undefined })}
              className="w-full text-sm border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All departments</option>
              {departments.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>

          {/* Rating range */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Min Rating
              </label>
              <input
                type="number"
                min={0}
                max={5}
                step={0.5}
                value={filters.min_rating ?? ""}
                onChange={(e) =>
                  update({
                    min_rating: e.target.value ? Number(e.target.value) : undefined,
                  })
                }
                placeholder="0"
                className="w-full text-sm border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Max Difficulty
              </label>
              <input
                type="number"
                min={0}
                max={5}
                step={0.5}
                value={filters.max_difficulty ?? ""}
                onChange={(e) =>
                  update({
                    max_difficulty: e.target.value ? Number(e.target.value) : undefined,
                  })
                }
                placeholder="5"
                className="w-full text-sm border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* Would take again & min reviews */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Min "Take Again" %
              </label>
              <input
                type="number"
                min={0}
                max={100}
                step={5}
                value={filters.min_would_take_again ?? ""}
                onChange={(e) =>
                  update({
                    min_would_take_again: e.target.value ? Number(e.target.value) : undefined,
                  })
                }
                placeholder="0"
                className="w-full text-sm border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Min # Reviews
              </label>
              <input
                type="number"
                min={0}
                step={1}
                value={filters.min_num_ratings ?? ""}
                onChange={(e) =>
                  update({
                    min_num_ratings: e.target.value ? Number(e.target.value) : undefined,
                  })
                }
                placeholder="0"
                className="w-full text-sm border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>

          {/* Tag filter */}
          {tags.length > 0 && (
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Tag
              </label>
              <select
                value={filters.tag || ""}
                onChange={(e) => update({ tag: e.target.value || undefined })}
                className="w-full text-sm border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Any tag</option>
                {tags.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Sort */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Sort By
              </label>
              <select
                value={filters.sort_by || "avg_rating"}
                onChange={(e) => update({ sort_by: e.target.value })}
                className="w-full text-sm border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="avg_rating">Rating</option>
                <option value="avg_difficulty">Difficulty</option>
                <option value="num_ratings"># Reviews</option>
                <option value="would_take_again_percent">Take Again %</option>
                <option value="last_name">Last Name</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Order
              </label>
              <select
                value={filters.sort_order || "desc"}
                onChange={(e) => update({ sort_order: e.target.value })}
                className="w-full text-sm border border-gray-200 rounded-lg px-2.5 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="desc">High to Low</option>
                <option value="asc">Low to High</option>
              </select>
            </div>
          </div>

          <button
            onClick={() =>
              onFiltersChange({
                school_id: schoolId,
                sort_by: "avg_rating",
                sort_order: "desc",
                limit: 50,
                offset: 0,
              })
            }
            className="w-full text-xs text-indigo-600 hover:text-indigo-800 font-medium py-1"
          >
            Reset all filters
          </button>
        </div>
      )}
    </div>
  );
}
