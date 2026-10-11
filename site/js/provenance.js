/**
 * ROAMINGPIGS.ORG — THE CRYPTOGRAPHIC PROVENANCE LEDGER & SCIENTIFIC REPO
 * Handles interactive waveform inspection across tactical codecs and BibTeX clipboard copying.
 */

document.addEventListener('DOMContentLoaded', () => {

  // =========================================================================
  // 1. TRCS WAVEFORM INSPECTOR ACROSS CODECS
  // =========================================================================
  const tabButtons = document.querySelectorAll('.waveform-tab-btn');
  const waveformTrace = document.getElementById('repoWaveTrace');
  const waveformSpec = document.getElementById('repoWaveSpec');
  const waveformWer = document.getElementById('repoWaveWer');
  const waveformAcoustic = document.getElementById('repoWaveAcoustic');

  const WAVEFORM_DATA = {
    'g711': {
      spec: 'ITU-T G.711: 8 kHz, 8-bit log PCM (64 kbps)',
      wer: '18.2% ± 1.1% WER',
      acoustic: 'Fricative /s/ collapse (300-3400 Hz 4th-order Butterworth)',
      path: 'M 0 70 Q 20 20, 40 70 T 80 70 T 120 70 T 160 70 T 200 70 T 240 70 T 280 70 T 320 70 T 360 70 T 400 70'
    },
    'amr': {
      spec: '3GPP TS 26.071: 8 kHz, ACELP (12.2 kbps)',
      wer: '24.6% ± 1.4% WER',
      acoustic: 'Linear prediction filter smearing nasal vowel anti-formants',
      path: 'M 0 70 Q 30 35, 60 70 T 120 70 T 180 70 T 240 70 T 300 70 T 360 70 T 400 70'
    },
    'gsm': {
      spec: 'ETSI GSM 06.10: 8 kHz, RPE-LTP (13.0 kbps)',
      wer: '22.9% ± 1.3% WER',
      acoustic: 'Regular pulse excitation distortion on tactical plosive bursts',
      path: 'M 0 70 Q 25 15, 50 70 T 100 70 T 150 70 T 200 70 T 250 70 T 300 70 T 350 70 T 400 70'
    },
    'opus': {
      spec: 'IETF RFC 6716: 8 kHz, SILK mode (12.0 kbps)',
      wer: '14.8% ± 0.9% WER',
      acoustic: 'Linear predictive noise shaping for narrowband tactical IP links',
      path: 'M 0 70 Q 15 25, 30 70 T 60 70 T 90 70 T 120 70 T 150 70 T 180 70 T 210 70 T 240 70 T 270 70 T 300 70 T 330 70 T 360 70 T 400 70'
    }
  };

  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tabButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const codecKey = btn.getAttribute('data-codec');
      const data = WAVEFORM_DATA[codecKey];
      if (data) {
        if (waveformTrace) waveformTrace.setAttribute('d', data.path);
        if (waveformSpec) waveformSpec.textContent = data.spec;
        if (waveformWer) waveformWer.textContent = data.wer;
        if (waveformAcoustic) waveformAcoustic.textContent = data.acoustic;
      }
    });
  });

  // =========================================================================
  // 2. BIBTEX & REPLICATION COMMAND CLIPBOARD COPY
  // =========================================================================
  function copyTextToClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise((resolve, reject) => {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      textarea.style.top = '0';
      textarea.setAttribute('readonly', '');
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      try {
        const success = document.execCommand('copy');
        document.body.removeChild(textarea);
        if (success) resolve();
        else reject(new Error('execCommand copy failed'));
      } catch (err) {
        document.body.removeChild(textarea);
        reject(err);
      }
    });
  }

  const copyButtons = document.querySelectorAll('.copy-btn');
  copyButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const el = document.getElementById(targetId);
      if (!el) return;

      const text = el.innerText || el.textContent;
      const origText = btn.textContent;
      copyTextToClipboard(text).then(() => {
        btn.textContent = 'COPIED';
        setTimeout(() => {
          btn.textContent = origText;
        }, 2000);
      }).catch(() => {
        btn.textContent = 'FAILED';
        setTimeout(() => {
          btn.textContent = origText;
        }, 2000);
      });
    });
  });

});
