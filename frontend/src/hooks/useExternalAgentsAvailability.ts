import { useEffect, useState } from 'react';
import { externalAgentsApi, type ExternalAgentStatus } from '../api';

export function useExternalAgentsAvailability() {
  const [agents, setAgents] = useState<ExternalAgentStatus[]>([]);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let active = true;
    let firstProbe = true;

    const probe = async () => {
      try {
        const items = await externalAgentsApi.getExternalAgents();
        if (active) {
          setAgents(items);
        }
      } catch {
        if (active) {
          setAgents([]);
        }
      } finally {
        if (active && firstProbe) {
          setChecking(false);
          firstProbe = false;
        }
      }
    };

    void probe();
    const intervalId = window.setInterval(() => {
      void probe();
    }, 15000);

    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, []);

  return { agents, checking };
}