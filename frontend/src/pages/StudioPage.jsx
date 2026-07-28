import { useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import NavBar from '../components/NavBar'
import ChatWidget from '../components/chat/ChatWidget'
import { MEDIA_COLORS } from '../store/mmStore'
import { studioDownloadUrl, useStudioStore } from '../store/studioStore'
import chainReporterLogo from '../assets/chainreporter-logo.png'
import rzPrimeLogo from '../assets/rz-prime-logo.png'
import coinHallLogo from '../assets/coin-hall-logo.png'
import metaCoinGuardLogo from '../assets/meta-coin-guard-logo.png'
import './StudioPage.css'

const BRAND_LOGOS = {
  ChainReporter: chainReporterLogo,
  'RZ Prime': rzPrimeLogo,
  'Coin Hall': coinHallLogo,
  'Meta Coin Guard': metaCoinGuardLogo,
}
const VOICES = ['News Anchor', 'Energetic', 'Calm Analyst', 'Persian Narrator']
const MUSIC = ['Breaking', 'Market Pulse', 'Luxury', 'Security Alert', 'Calm Analysis']
const ACTIVE_STATUSES = new Set(['pending', 'in_progress'])

function Icon({ name, size = 15 }) {
  const paths = {
    up: <path d="m18 15-6-6-6 6" />,
    down: <path d="m6 9 6 6 6-6" />,
    close: <path d="M18 6 6 18M6 6l12 12" />,
    save: <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2ZM17 21v-8H7v8M7 3v5h8" />,
    spark: <path d="m12 3-1.5 4.5L6 9l4.5 1.5L12 15l1.5-4.5L18 9l-4.5-1.5L12 3Zm-6 9-.8 2.2L3 15l2.2.8L6 18l.8-2.2L9 15l-2.2-.8L6 12Z" />,
    video: <path d="m15 10 4.6-2.3a1 1 0 0 1 1.4.9v6.8a1 1 0 0 1-1.4.9L15 14M4 6h9a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2Z" />,
    download: <path d="M12 3v12m0 0 4-4m-4 4-4-4M5 21h14" />,
    retry: <path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7" />,
    refresh: <path d="M20 6v5h-5M4 18v-5h5M18.7 9A7 7 0 0 0 6.3 6.3L4 9m16 6-2.3 2.7A7 7 0 0 1 5.3 15" />,
  }
  return (
    <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
      {paths[name]}
    </svg>
  )
}

function statusLabel(status) {
  return ({
    pending: 'Queued',
    in_progress: 'Generating',
    completed: 'Completed',
    failed: 'Failed',
    cancelled: 'Cancelled',
    expired: 'Expired',
  })[status] || status || 'Draft'
}

function formatDate(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function StoryTray() {
  const cards = useStudioStore(state => state.importedCards)
  const removeCard = useStudioStore(state => state.removeCard)
  const moveCard = useStudioStore(state => state.moveCard)
  const clearTray = useStudioStore(state => state.clearTray)
  const groups = useMemo(() => {
    const result = []
    cards.forEach(card => {
      let group = result.find(item => item.brand === card.media)
      if (!group) {
        group = { brand: card.media, cards: [] }
        result.push(group)
      }
      group.cards.push(card)
    })
    return result
  }, [cards])

  return (
    <aside className="studio-panel studio-story-panel" aria-label="Imported stories">
      <div className="studio-panel-heading">
        <div>
          <span className="studio-eyebrow">Source tray</span>
          <h2>Imported stories <span className="studio-count">{cards.length}</span></h2>
        </div>
        {cards.length > 0 && <button type="button" className="studio-text-button" onClick={clearTray}>Clear</button>}
      </div>

      {!cards.length ? (
        <div className="studio-empty-tray">
          <div className="studio-empty-icon"><Icon name="video" size={20} /></div>
          <p>Send stories from Multimedia to start a reel.</p>
          <Link to="/multimedia" className="studio-secondary-link">Open Multimedia</Link>
        </div>
      ) : (
        <div className="studio-story-groups">
          {groups.map(group => (
            <section key={group.brand} className="studio-story-group">
              <div className="studio-group-label">
                <span className="studio-brand-dot" style={{ background: MEDIA_COLORS[group.brand] || '#7a8499' }} />
                <span>{group.brand}</span>
                <span>{group.cards.length}</span>
              </div>
              <div className="studio-story-list">
                {group.cards.map((card, index) => (
                  <article key={`${card.media}:${card.id}`} className="studio-story-row">
                    <div className="studio-story-number">{String(index + 1).padStart(2, '0')}</div>
                    <div className="studio-story-copy">
                      <h3 data-no-localize="true">{card.headline}</h3>
                      <p>{card.source || 'News source'}{card.timeAgo ? ` / ${card.timeAgo}` : ''}</p>
                    </div>
                    <div className="studio-story-actions">
                      <button type="button" title="Move up" aria-label="Move story up" onClick={() => moveCard(card.id, card.media, -1)} disabled={index === 0}><Icon name="up" size={13} /></button>
                      <button type="button" title="Move down" aria-label="Move story down" onClick={() => moveCard(card.id, card.media, 1)} disabled={index === group.cards.length - 1}><Icon name="down" size={13} /></button>
                      <button type="button" title="Remove" aria-label="Remove story" onClick={() => removeCard(card.id, card.media)}><Icon name="close" size={13} /></button>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </aside>
  )
}

function PhonePreview({ job }) {
  const cards = useStudioStore(state => state.importedCards)
  const script = useStudioStore(state => state.script)
  const settings = useStudioStore(state => state.settings)
  const primary = cards[0]
  const shots = script?.shots?.length ? script.shots : cards.map((card, index) => ({
    start: `${index * Math.max(1, Math.floor(settings.duration / Math.max(cards.length, 1)))}s`,
    visual: card.headline,
    caption: card.headline,
  }))
  const active = ACTIVE_STATUSES.has(job?.status)
  const completed = job?.status === 'completed'

  return (
    <section className="studio-preview-column" aria-label="Reel preview">
      <div className="studio-preview-toolbar">
        <div>
          <span className="studio-eyebrow">Live composition</span>
          <h2>Reel preview</h2>
        </div>
        <div className="studio-format-badges"><span>9:16</span><span>{settings.duration}s</span><span>{settings.resolution}</span></div>
      </div>

      <div className={`studio-phone studio-mood-${settings.music.toLowerCase().replaceAll(' ', '-')}`}>
        <div className="studio-phone-speaker" />
        <div className="studio-phone-screen">
          {completed ? (
            <video key={job.id} className="studio-video" controls playsInline preload="metadata" crossOrigin="use-credentials" src={studioDownloadUrl(job.id)} />
          ) : (
            <>
              <div className="studio-reel-surface" />
              <div className="studio-reel-topline">
                <img src={BRAND_LOGOS[primary?.media] || chainReporterLogo} alt="" />
                <span>{primary?.media || 'ChainReporter'}</span>
                <span className="studio-live-label">REEL</span>
              </div>
              <div className="studio-reel-center">
                <span className="studio-reel-kicker">{script?.directorBrief?.formatName || settings.music}</span>
                <h3 data-no-localize="true">{script?.hook || primary?.headline || 'Your next news reel starts here'}</h3>
                <p data-no-localize="true">{script?.directorBrief?.visualConcept || script?.on_screen_captions?.[0] || 'Add one or more stories, then generate the script and storyboard.'}</p>
              </div>
              <div className="studio-reel-footer">
                <div className="studio-reel-progress"><span style={{ width: active ? '42%' : script ? '100%' : '12%' }} /></div>
                <div><span>{settings.voice}</span><span>{settings.language}</span></div>
              </div>
              {active && (
                <div className="studio-generating-overlay">
                  <span className="studio-loader" />
                  <strong>{statusLabel(job.status)}</strong>
                  <p>Video generation can take several minutes.</p>
                </div>
              )}
              {job?.status === 'failed' && (
                <div className="studio-generating-overlay studio-generation-failed">
                  <strong>Generation failed</strong>
                  <p>{job.error || 'OpenRouter could not complete this reel.'}</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <div className="studio-storyboard-strip" aria-label="Storyboard frames">
        {(shots.length ? shots : [{ start: '0s', visual: 'Add stories to build the storyboard' }]).slice(0, 5).map((shot, index) => (
          <div key={`${shot.start}-${index}`} className="studio-frame">
            <span>{shot.start || `${index * 6}s`}</span>
            <p data-no-localize="true">{shot.caption || shot.visual}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

function StudioControls() {
  const cards = useStudioStore(state => state.importedCards)
  const models = useStudioStore(state => state.models)
  const settings = useStudioStore(state => state.settings)
  const script = useStudioStore(state => state.script)
  const title = useStudioStore(state => state.title)
  const modelLoading = useStudioStore(state => state.modelLoading)
  const draftSaving = useStudioStore(state => state.draftSaving)
  const scriptLoading = useStudioStore(state => state.scriptLoading)
  const directorLoading = useStudioStore(state => state.directorLoading)
  const generating = useStudioStore(state => state.generating)
  const setSetting = useStudioStore(state => state.setSetting)
  const setTitle = useStudioStore(state => state.setTitle)
  const setScriptField = useStudioStore(state => state.setScriptField)
  const setCaptions = useStudioStore(state => state.setCaptions)
  const setDirectorField = useStudioStore(state => state.setDirectorField)
  const saveDraft = useStudioStore(state => state.saveDraft)
  const generateScript = useStudioStore(state => state.generateScript)
  const generateDirection = useStudioStore(state => state.generateDirection)
  const generateVideo = useStudioStore(state => state.generateVideo)
  const selectedModel = models.find(model => model.id === settings.model)
  const canWork = cards.length > 0
  const nativeAudio = selectedModel?.generateAudio === true
  const directorBrief = script?.directorBrief

  return (
    <aside className="studio-panel studio-controls" aria-label="Reel controls">
      <div className="studio-panel-heading">
        <div>
          <span className="studio-eyebrow">Production desk</span>
          <h2>Reel controls</h2>
        </div>
        <button type="button" className="studio-icon-text-button" onClick={() => saveDraft().catch(() => {})} disabled={!canWork || draftSaving}>
          <Icon name="save" /> {draftSaving ? 'Saving' : 'Save'}
        </button>
      </div>

      <div className="studio-control-scroll">
        <label className="studio-field">
          <span>Draft title</span>
          <input value={title} onChange={event => setTitle(event.target.value)} placeholder="Untitled reel" disabled={!canWork} />
        </label>

        <div className="studio-field-row studio-format-row">
          <label className="studio-field">
            <span>Length</span>
            <select value={settings.duration} onChange={event => setSetting('duration', Number(event.target.value))} disabled={!selectedModel?.durations?.length}>
              {(selectedModel?.durations || []).map(duration => <option key={duration} value={duration}>{duration} seconds</option>)}
            </select>
          </label>
          <label className="studio-field">
            <span>Resolution</span>
            <select value={settings.resolution} onChange={event => setSetting('resolution', event.target.value)} disabled={!selectedModel?.resolutions?.length}>
              {(selectedModel?.resolutions || []).map(resolution => <option key={resolution} value={resolution}>9:16 / {resolution}</option>)}
            </select>
          </label>
        </div>

        <label className="studio-field">
          <span>Video model</span>
          <select value={settings.model} onChange={event => setSetting('model', event.target.value)} disabled={modelLoading || !models.length}>
            {!models.length && <option value="">{modelLoading ? 'Loading video models...' : 'No 9:16 models available'}</option>}
            {models.map(model => <option key={model.id} value={model.id}>{model.name}</option>)}
          </select>
          {selectedModel?.pricePerSecond && <small>From ${selectedModel.pricePerSecond} per video second</small>}
        </label>

        <div className="studio-field-row">
          <label className="studio-field">
            <span>Language</span>
            <select value={settings.language} onChange={event => setSetting('language', event.target.value)}>
              <option>English</option>
              <option>Persian</option>
            </select>
          </label>
          <label className="studio-field">
            <span>Music mood</span>
            <select value={settings.music} onChange={event => setSetting('music', event.target.value)} disabled={!nativeAudio}>
              {MUSIC.map(mood => <option key={mood}>{mood}</option>)}
            </select>
          </label>
        </div>

        <fieldset className="studio-fieldset" disabled={!nativeAudio}>
          <legend>Narration voice</legend>
          <div className="studio-voice-grid">
            {VOICES.map(voice => (
              <button key={voice} type="button" className={settings.voice === voice ? 'active' : ''} onClick={() => setSetting('voice', voice)}>{voice}</button>
            ))}
          </div>
        </fieldset>

        <label className="studio-field">
          <span>Visual direction</span>
          <textarea rows="3" value={settings.visualDirection} onChange={event => setSetting('visualDirection', event.target.value)} />
        </label>

        <div className="studio-script-heading">
          <span>Script and captions</span>
          <button type="button" className="studio-generate-script" onClick={() => generateScript().catch(() => {})} disabled={!canWork || scriptLoading}>
            <Icon name="spark" /> {scriptLoading ? 'Writing...' : script ? 'Rewrite' : 'Generate script'}
          </button>
        </div>

        {script ? (
          <div className="studio-script-fields">
            <label className="studio-field"><span>Hook</span><textarea rows="2" value={script.hook || ''} onChange={event => setScriptField('hook', event.target.value)} data-no-localize="true" /></label>
            <label className="studio-field"><span>Narration</span><textarea rows="6" value={script.narration || ''} onChange={event => setScriptField('narration', event.target.value)} data-no-localize="true" /></label>
            <label className="studio-field"><span>On-screen captions</span><textarea rows="4" value={(script.on_screen_captions || []).join('\n')} onChange={event => setCaptions(event.target.value)} data-no-localize="true" /></label>
            <label className="studio-field"><span>Call to action</span><input value={script.cta || ''} onChange={event => setScriptField('cta', event.target.value)} data-no-localize="true" /></label>
          </div>
        ) : (
          <div className="studio-script-empty">Studio will turn the selected facts into an editable narration and shot list.</div>
        )}

        <div className="studio-script-heading">
          <span>Art direction</span>
          <button type="button" className="studio-generate-script" onClick={() => generateDirection().catch(() => {})} disabled={!script || directorLoading}>
            <Icon name="spark" /> {directorLoading ? 'Directing...' : directorBrief ? 'Redirect' : 'Create direction'}
          </button>
        </div>

        {directorBrief ? (
          <div className="studio-director-review">
            <div className="studio-director-format">
              <span>{directorBrief.formatName}</span>
              <small>{directorBrief.styleSystemName}</small>
            </div>
            <label className="studio-field"><span>Visual concept</span><textarea rows="2" value={directorBrief.visualConcept || ''} onChange={event => setDirectorField('visualConcept', event.target.value)} data-no-localize="true" /></label>
            <div className="studio-field-row">
              <label className="studio-field"><span>Hero object</span><input value={directorBrief.heroObject || ''} onChange={event => setDirectorField('heroObject', event.target.value)} data-no-localize="true" /></label>
              <label className="studio-field"><span>Camera</span><input value={directorBrief.camera || ''} onChange={event => setDirectorField('camera', event.target.value)} data-no-localize="true" /></label>
            </div>
            <label className="studio-field"><span>Palette</span><input value={directorBrief.palette || ''} onChange={event => setDirectorField('palette', event.target.value)} data-no-localize="true" /></label>
            <label className="studio-field"><span>Composition</span><textarea rows="2" value={directorBrief.composition || ''} onChange={event => setDirectorField('composition', event.target.value)} data-no-localize="true" /></label>
            <label className="studio-field"><span>Transitions</span><input value={directorBrief.transitionLanguage || ''} onChange={event => setDirectorField('transitionLanguage', event.target.value)} data-no-localize="true" /></label>
            <div className="studio-motion-plan">
              {(directorBrief.motionArc || []).map((beat, index) => <p key={`${index}-${beat}`}><span>{index + 1}</span>{beat}</p>)}
            </div>
          </div>
        ) : (
          <div className="studio-script-empty">Create a director brief to review the format, visual concept, hero object, and motion plan.</div>
        )}
      </div>

      <button type="button" className="studio-primary-action" onClick={() => generateVideo().catch(() => {})} disabled={!canWork || !script || !directorBrief || !settings.model || generating}>
        {generating ? <span className="studio-loader studio-loader-dark" /> : <Icon name="video" size={17} />}
        {generating ? 'Submitting reel...' : 'Generate reel'}
      </button>
      <p className="studio-audio-note">{nativeAudio ? 'Narration and original mood music are generated by the selected video model.' : 'This model does not support native audio. Choose an audio-capable model for narration and music.'}</p>
    </aside>
  )
}

function JobHistory() {
  const jobs = useStudioStore(state => state.jobs)
  const jobsLoading = useStudioStore(state => state.jobsLoading)
  const polling = useStudioStore(state => state.polling)
  const pollJob = useStudioStore(state => state.pollJob)
  const generateVideo = useStudioStore(state => state.generateVideo)

  return (
    <section className="studio-history">
      <div className="studio-history-heading">
        <div><span className="studio-eyebrow">Recent output</span><h2>Studio history</h2></div>
        <span>{jobs.length} {jobs.length === 1 ? 'job' : 'jobs'}</span>
      </div>
      {!jobs.length ? (
        <p className="studio-history-empty">{jobsLoading ? 'Loading recent reels...' : 'Generated reels will appear here with preview and download controls.'}</p>
      ) : (
        <div className="studio-job-list">
          {jobs.map(job => (
            <article key={job.id} className="studio-job-row">
              <div className={`studio-job-status status-${job.status}`}><span />{statusLabel(job.status)}</div>
              <div className="studio-job-main">
                <h3>{job.settings?.music || 'News'} reel</h3>
                <p>{job.model} / {job.settings?.duration || 30}s / {formatDate(job.createdAt)}</p>
                {job.error && <small>{job.error}</small>}
              </div>
              <div className="studio-job-cost">{job.cost == null ? 'Cost pending' : `$${Number(job.cost).toFixed(3)}`}</div>
              <div className="studio-job-actions">
                {ACTIVE_STATUSES.has(job.status) && (
                  <button type="button" title="Refresh status" aria-label="Refresh job status" onClick={() => pollJob(job.id)} disabled={polling[job.id]}><Icon name="refresh" /></button>
                )}
                {job.status === 'completed' && (
                  <a href={studioDownloadUrl(job.id, true)} download={`chainreporter-reel-${job.id}.mp4`} title="Download MP4" aria-label="Download MP4"><Icon name="download" /></a>
                )}
                {['failed', 'cancelled', 'expired'].includes(job.status) && (
                  <button type="button" title="Retry with current draft" aria-label="Retry reel" onClick={() => generateVideo().catch(() => {})}><Icon name="retry" /></button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

export default function StudioPage() {
  const jobs = useStudioStore(state => state.jobs)
  const error = useStudioStore(state => state.error)
  const notice = useStudioStore(state => state.notice)
  const fetchModels = useStudioStore(state => state.fetchModels)
  const fetchJobs = useStudioStore(state => state.fetchJobs)
  const pollJob = useStudioStore(state => state.pollJob)
  const clearMessages = useStudioStore(state => state.clearMessages)
  const previewJob = jobs.find(job => ACTIVE_STATUSES.has(job.status)) || jobs.find(job => job.status === 'completed') || jobs[0]
  const activeKey = jobs.filter(job => ACTIVE_STATUSES.has(job.status)).map(job => `${job.id}:${job.status}`).join('|')

  useEffect(() => {
    fetchModels()
    fetchJobs()
  }, [fetchModels, fetchJobs])

  useEffect(() => {
    const active = useStudioStore.getState().jobs.filter(job => ACTIVE_STATUSES.has(job.status))
    if (!active.length) return undefined
    const firstCheck = window.setTimeout(() => active.forEach(job => pollJob(job.id)), 2000)
    const interval = window.setInterval(() => {
      useStudioStore.getState().jobs.filter(job => ACTIVE_STATUSES.has(job.status)).forEach(job => pollJob(job.id))
    }, 30000)
    return () => {
      window.clearTimeout(firstCheck)
      window.clearInterval(interval)
    }
  }, [activeKey, pollJob])

  useEffect(() => {
    if (!error && !notice) return undefined
    const timer = window.setTimeout(clearMessages, error ? 9000 : 3500)
    return () => window.clearTimeout(timer)
  }, [error, notice, clearMessages])

  return (
    <>
      <NavBar />
      <main className="studio-page">
        <header className="studio-page-header">
          <div>
            <span className="studio-eyebrow">Short-form newsroom</span>
            <h1>Studio</h1>
            <p>Turn selected reporting into a narrated Instagram reel.</p>
          </div>
          <Link to="/multimedia" className="studio-back-link">Back to Multimedia</Link>
        </header>

        {(error || notice) && (
          <div className={`studio-toast ${error ? 'studio-toast-error' : 'studio-toast-success'}`} role="status">
            <span>{error || notice}</span>
            <button type="button" onClick={clearMessages} aria-label="Dismiss"><Icon name="close" size={14} /></button>
          </div>
        )}

        <div className="studio-workspace">
          <StoryTray />
          <PhonePreview job={previewJob} />
          <StudioControls />
        </div>
        <JobHistory />
      </main>
      <ChatWidget />
    </>
  )
}
