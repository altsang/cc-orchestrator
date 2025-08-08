// Connection status indicator component

import React from 'react';

interface ConnectionStatusProps {
  isConnected: boolean;
  isReconnecting?: boolean;
  className?: string;
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ 
  isConnected, 
  isReconnecting = false,
  className = '' 
}) => {
  if (isConnected) {
    return (
      <div className={`flex items-center gap-2 text-sm text-green-600 ${className}`}>
        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
        <span>Connected</span>
      </div>
    );
  }

  if (isReconnecting) {
    return (
      <div className={`flex items-center gap-2 text-sm text-yellow-600 ${className}`}>
        <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></div>
        <span>Reconnecting...</span>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 text-sm text-red-600 ${className}`}>
      <div className="w-2 h-2 bg-red-500 rounded-full"></div>
      <span>Disconnected</span>
    </div>
  );
};