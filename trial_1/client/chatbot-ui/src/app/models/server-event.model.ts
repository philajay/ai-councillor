
export interface ServerEvent {
    action: 'functionCall' | 'endOfTurn' | 'text';
    name?: string;
    text?: string;
    endOfTurn?: boolean;
    results?: any;
    agent?:string;
    isIntermediateMessage?: boolean;
    progress_spinner?: 'start' | 'end';
  }
