/**
 * Swizzled Mermaid component to wrap with BrowserOnly.
 * This fixes the SSR/SSG errors during static site generation.
 */
import React from 'react';
import BrowserOnly from '@docusaurus/BrowserOnly';

export default function Mermaid(props) {
    return (
        <BrowserOnly fallback={<div style={{ padding: '1rem', background: '#f0f4f8', borderRadius: '4px', color: '#666', fontFamily: 'monospace', fontSize: '12px' }}>Loading diagram...</div>}>
            {() => {
                // eslint-disable-next-line global-require
                const MermaidOriginal = require('@theme-original/Mermaid').default;
                return <MermaidOriginal {...props} />;
            }}
        </BrowserOnly>
    );
}
