// Mobile navigation menu component

import React from 'react';

interface Tab {
  id: string;
  label: string;
  icon: string;
}

interface MobileMenuProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export const MobileMenu: React.FC<MobileMenuProps> = ({ tabs, activeTab, onTabChange, isOpen, onToggle }) => {
  const handleTabSelect = (tab: string) => {
    onTabChange(tab);
  };

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        aria-expanded={false}
        className="md:hidden flex items-center px-3 py-2 border rounded text-gray-500 border-gray-600 hover:text-white hover:border-white"
        aria-label="Open menu"
      >
        <svg className="fill-current h-3 w-3" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
          <title>Menu</title>
          <path d="M0 3h20v2H0V3zm0 6h20v2H0V9zm0 6h20v2H0v-2z"/>
        </svg>
      </button>
    );
  }

  return (
    <div className="md:hidden">
      <button
        onClick={onToggle}
        aria-expanded={true}
        className="flex items-center px-3 py-2 border rounded text-gray-500 border-gray-600 hover:text-white hover:border-white"
        aria-label="Close menu"
      >
        <svg className="fill-current h-3 w-3" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
          <title>Close</title>
          <path d="M10 8.586L2.929 1.515 1.515 2.929 8.586 10l-7.071 7.071 1.414 1.414L10 11.414l7.071 7.071 1.414-1.414L11.414 10l7.071-7.071-1.414-1.414L10 8.586z"/>
        </svg>
      </button>

      <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabSelect(tab.id)}
            className={`block px-3 py-2 rounded-md text-base font-medium w-full text-left ${
              activeTab === tab.id
                ? 'text-blue-600 bg-blue-50'
                : 'text-gray-600 hover:text-gray-800 hover:bg-gray-50'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
};
