import { useState, useEffect, useCallback } from "react";
import { Search, Loader2, School as SchoolIcon, Check } from "lucide-react";
import { searchSchools, bootstrapSchool, getSavedSchools } from "../api";
import type { School, BootstrapStatus } from "../api";

interface Props {
  onSchoolSelected: (school: School) => void;
}

export default function SchoolSelector({ onSchoolSelected }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<School[]>([]);
  const [savedSchools, setSavedSchools] = useState<School[]>([]);
  const [loading, setLoading] = useState(false);
  const [bootstrapping, setBootstrapping] = useState(false);
  const [bootstrapInfo, setBootstrapInfo] = useState<BootstrapStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getSavedSchools()
      .then(setSavedSchools)
      .catch(() => {});
  }, []);

  const handleSearch = useCallback(async () => {
    if (query.length < 2) return;
    setLoading(true);
    setError("");
    try {
      const schools = await searchSchools(query);
      setResults(schools);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }, [query]);

  const handleSelect = async (school: School) => {
    setBootstrapping(true);
    setError("");
    setBootstrapInfo(null);
    try {
      const status = await bootstrapSchool(school.id);
      setBootstrapInfo(status);
      onSchoolSelected(school);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load school data");
    } finally {
      setBootstrapping(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[500px] p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-indigo-100 rounded-2xl mb-3">
            <SchoolIcon className="w-7 h-7 text-indigo-600" />
          </div>
          <h1 className="text-xl font-bold text-gray-900">Better RMP</h1>
          <p className="text-sm text-gray-500 mt-1">
            Find your school to get started
          </p>
        </div>

        {savedSchools.length > 0 && (
          <div className="mb-4">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
              Saved Schools
            </p>
            <div className="space-y-1">
              {savedSchools.map((school) => (
                <button
                  key={school.id}
                  onClick={() => onSchoolSelected(school)}
                  className="w-full text-left px-3 py-2 rounded-lg bg-indigo-50 hover:bg-indigo-100 transition-colors flex items-center gap-2"
                >
                  <Check className="w-4 h-4 text-indigo-600 flex-shrink-0" />
                  <div>
                    <div className="text-sm font-medium text-gray-900">{school.name}</div>
                    {school.city && school.state && (
                      <div className="text-xs text-gray-500">
                        {school.city}, {school.state}
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </div>
            <div className="border-t border-gray-200 my-4" />
          </div>
        )}

        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search for your university..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="w-full pl-9 pr-3 py-2.5 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white"
          />
        </div>

        <button
          onClick={handleSearch}
          disabled={loading || query.length < 2}
          className="w-full py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            "Search Schools"
          )}
        </button>

        {error && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {bootstrapping && (
          <div className="mt-3 p-3 bg-indigo-50 border border-indigo-200 rounded-lg text-sm text-indigo-700 flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading professor data... This may take a moment.
          </div>
        )}

        {bootstrapInfo && (
          <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
            Loaded {bootstrapInfo.professor_count} professors from{" "}
            {bootstrapInfo.school_name}
          </div>
        )}

        {results.length > 0 && !bootstrapping && (
          <div className="mt-3 max-h-64 overflow-y-auto space-y-1 border border-gray-200 rounded-xl p-2 bg-white">
            {results.map((school) => (
              <button
                key={school.id}
                onClick={() => handleSelect(school)}
                className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="text-sm font-medium text-gray-900">
                  {school.name}
                </div>
                {school.city && school.state && (
                  <div className="text-xs text-gray-500">
                    {school.city}, {school.state}
                  </div>
                )}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
