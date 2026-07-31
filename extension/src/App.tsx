import { useState, useEffect } from "react";
import SchoolSelector from "./components/SchoolSelector";
import SearchView from "./components/SearchView";
import type { School } from "./api";

function App() {
  const [school, setSchool] = useState<School | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem("better_rmp_school");
    if (saved) {
      try {
        setSchool(JSON.parse(saved));
      } catch {
        // ignore
      }
    }
  }, []);

  const handleSchoolSelected = (s: School) => {
    setSchool(s);
    localStorage.setItem("better_rmp_school", JSON.stringify(s));
  };

  const handleChangeSchool = () => {
    setSchool(null);
    localStorage.removeItem("better_rmp_school");
  };

  if (!school) {
    return <SchoolSelector onSchoolSelected={handleSchoolSelected} />;
  }

  return <SearchView school={school} onChangeSchool={handleChangeSchool} />;
}

export default App;
