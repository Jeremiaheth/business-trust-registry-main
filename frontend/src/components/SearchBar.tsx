import { Search } from "lucide-react";
import { FormEvent, useState } from "react";

interface SearchBarProps {
  initialValue?: string;
  label?: string;
  placeholder?: string;
  onSearch: (query: string) => void;
}

export function SearchBar({
  initialValue = "",
  label = "Find a Business",
  placeholder = "Search by business name, BTR ID, identifier, or public tag",
  onSearch
}: SearchBarProps) {
  const [query, setQuery] = useState(initialValue);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSearch(query);
  }

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <label className="search-label" htmlFor="portal-search">
        {label}
      </label>
      <div className="search-input-shell">
        <Search aria-hidden="true" className="search-icon" />
        <input
          id="portal-search"
          name="query"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={placeholder}
        />
        <button type="submit">Search Businesses</button>
      </div>
    </form>
  );
}
