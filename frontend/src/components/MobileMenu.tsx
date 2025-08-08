// Mobile navigation menu component

import React, { useState } from 'react';

interface MobileMenuProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export const MobileMenu: React.FC<MobileMenuProps> = ({ activeTab, onTabChange }) => {
  const [isOpen, setIsOpen] = useState(false);

  const tabs = [
    { key: 'overview', label: 'Overview', icon: '📊' },
    { key: 'instances', label: 'Instances', icon: '💻' },
    { key: 'tasks', label: 'Tasks', icon: '📋' },
  ];

  const handleTabSelect = (tab: string) => {
    onTabChange(tab);
    setIsOpen(false);
  };

  return (
    <div className="lg:hidden">
      {/* Mobile menu button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center justify-center p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
        aria-expanded="false"
      >
        <span className="sr-only">Open main menu</span>
        {!isOpen ? (
          <svg className="block h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        ) : (
          <svg className="block h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        )}
      </button>

      {/* Mobile menu overlay */}
      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-gray-600 bg-opacity-50"
            onClick={() => setIsOpen(false)}
          ></div>
          <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-md shadow-lg z-50 border border-gray-200">
            <div className="py-1">
              {tabs.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => handleTabSelect(tab.key)}
                  className={`flex items-center w-full px-4 py-2 text-sm text-left hover:bg-gray-100 ${
                    activeTab === tab.key
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : 'text-gray-700'
                  }`}
                >
                  <span className="mr-3 text-lg">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};
