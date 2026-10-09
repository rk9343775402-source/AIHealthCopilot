import { useCallback, useEffect, useMemo, useState } from "react";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const NAV_GROUPS = [
  { label: "Overview", items: ["Dashboard", "Health Timeline"] },
  { label: "Your health", items: ["Medical Records", "Lab Results", "Medicines", "Doctor Visits", "Health Profile"] },
  { label: "Support", items: ["Injury Assistant", "Animal Bite Assistant", "Emergency Mode", "AI Companion", "Wellbeing"] },
  { label: "Connected care", items: ["FHIR / ABDM", "Settings"] },
];
const ROUTES = {
  "Medical Records": "/api/medical-documents",
  "Lab Results": "/api/lab-results",
  Medicines: "/api/medicines",
  "Injury Assistant": "/api/injuries",
  "Animal Bite Assistant": "/api/animal-bites",
  "Emergency Mode": "/api/emergency-events",
  "Doctor Visits": "/api/doctor-visits",
  Wellbeing: "/api/wellbeing",
};
const PAGE_META = {
  Dashboard: ["Your health, in one place", "A clear view of the information connected to your account."],
  "Health Timeline": ["Health timeline", "A chronological view of events returned by your health record."],
  "Medical Records": ["Medical records", "Add a record or upload a document to your health record."],
  "Lab Results": ["Lab results", "Review and add laboratory results. Values are shown as returned by your care team."],
  Medicines: ["Medicines", "Keep a record of medicines and instructions shared with you."],
  "Doctor Visits": ["Doctor visits", "Prepare a record-grounded summary for your next clinical visit."],
  "Health Profile": ["Health profile", "Review the health profile returned by the connected service."],
  "Injury Assistant": ["Injury support", "Share details to record an injury and request available guidance."],
  "Animal Bite Assistant": ["Animal bite support", "Record a bite and request available guidance. This is not a substitute for urgent medical care."],
  "Emergency Mode": ["Emergency mode", "If someone may be in immediate danger, contact your local emergency service now."],
  "AI Companion": ["AI health companion", "Ask a question. Responses depend on the connected service and available health information."],
  Wellbeing: ["Wellbeing check-in", "Record how you are feeling. Your entries are sent to the connected service."],
  "FHIR / ABDM": ["Connected health data", "Request the FHIR patient resource, bundle, or ABDM mock response for the selected user."],
  Settings: ["Settings", "Manage the active user and the API connection used by this application."],
};
const HI = {
  "Overview": "अवलोकन", "Your health": "आपका स्वास्थ्य", "Support": "सहायता", "Connected care": "जुड़ी स्वास्थ्य सेवाएँ",
  "Dashboard": "डैशबोर्ड", "Health Timeline": "स्वास्थ्य समयरेखा", "Medical Records": "चिकित्सा रिकॉर्ड",
  "Lab Results": "लैब परिणाम", "Medicines": "दवाइयाँ", "Doctor Visits": "डॉक्टर से मुलाक़ात",
  "Health Profile": "स्वास्थ्य प्रोफ़ाइल", "Injury Assistant": "चोट सहायता", "Animal Bite Assistant": "जानवर के काटने की सहायता",
  "Emergency Mode": "आपातकालीन मोड", "AI Companion": "AI स्वास्थ्य सहायक", "Wellbeing": "तंदुरुस्ती",
  "FHIR / ABDM": "FHIR / ABDM", "Settings": "सेटिंग्स",
  "Your health, in one place": "आपका स्वास्थ्य, एक जगह",
  "Health timeline": "स्वास्थ्य समयरेखा", "Medical records": "चिकित्सा रिकॉर्ड",
  "Lab results": "लैब परिणाम", "Connected health data": "जुड़ा हुआ स्वास्थ्य डेटा",
  "Injury support": "चोट सहायता", "Animal bite support": "जानवर के काटने की सहायता",
  "Emergency mode": "आपातकालीन मोड", "AI health companion": "AI स्वास्थ्य सहायक",
  "Wellbeing check-in": "तंदुरुस्ती की जाँच", "Prepare a record-grounded summary for your next clinical visit.": "अपने अगले चिकित्सकीय परामर्श के लिए रिकॉर्ड-आधारित सारांश तैयार करें।",
  "Test name": "जाँच का नाम", "Result value": "परिणाम", "Unit": "इकाई",
  "Reference range": "संदर्भ सीमा", "Status": "स्थिति", "Test date": "जाँच की तारीख",
  "Medicine name": "दवा का नाम", "Strength": "ताकत", "How often": "कितनी बार",
  "Start date": "शुरू करने की तारीख", "End date": "समाप्ति की तारीख",
  "Record title": "रिकॉर्ड का शीर्षक", "Record type": "रिकॉर्ड का प्रकार",
  "Document date": "दस्तावेज़ की तारीख", "Affected area": "प्रभावित जगह",
  "Describe what happened and symptoms": "क्या हुआ और लक्षण बताएं",
  "Describe the bite or scratch": "काटने या खरोंच का विवरण दें",
  "What is happening?": "क्या हो रहा है?", "Additional details": "अतिरिक्त जानकारी",
  "How are you feeling?": "आप कैसा महसूस कर रहे हैं?", "Date": "तारीख",
  "Clinician / clinic": "चिकित्सक / क्लिनिक", "Visit date": "मुलाक़ात की तारीख",
  "Reason for visit": "मुलाक़ात का कारण", "Visit notes": "मुलाक़ात के नोट्स",
  "Save record": "रिकॉर्ड सहेजें", "Save": "सहेजें", "Refresh": "रीफ़्रेश",
  "Create a profile": "प्रोफ़ाइल बनाएँ", "Full name": "पूरा नाम",
  "Email address": "ईमेल पता", "Phone number": "फ़ोन नंबर",
};
const translate = (text, language) => language === "hi" ? HI[text] || text : text;

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  const text = await response.text();
  let body;
  try { body = text ? JSON.parse(text) : null; } catch { body = text; }
  if (!response.ok) {
    const detail = body && typeof body === "object" ? body.detail || body.message || body.error : body;
    throw new Error(detail ? `${response.status}: ${detail}` : `Request failed (${response.status})`);
  }
  return body;
}

function asList(value) {
  if (Array.isArray(value)) return value;
  if (!value || typeof value !== "object") return [];
  for (const key of ["items", "results", "data", "records", "users", "documents", "lab_results", "medicines", "events", "timeline"]) {
    if (Array.isArray(value[key])) return value[key];
  }
  return [value];
}

function toPath(path, userId) {
  if (!userId) return path;
  return `${path.replace(/\/$/, "")}/${encodeURIComponent(userId)}`;
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("The selected image could not be read."));
    reader.onload = () => typeof reader.result === "string" ? resolve(reader.result) : reject(new Error("Invalid image data."));
    reader.readAsDataURL(file);
  });
}

function Icon({ name }) {
  const paths = {
    Dashboard: "M3 3h8v8H3zM13 3h8v5h-8zM13 10h8v11h-8zM3 13h8v8H3z",
    "Health Timeline": "M4 12h4l3-8 4 16 3-8h2",
    "Medical Records": "M6 3h9l4 4v14H6zM14 3v5h5M9 13h7M9 17h7",
    "Lab Results": "M9 3h6M10 3v7l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3M8 15h8",
    Medicines: "M8 4a4 4 0 0 0-4 4v8a4 4 0 0 0 8 0V8a4 4 0 0 0-4-4zM8 12h4M16 6l5 5M15 7l4-4",
    "Health Profile": "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0",
    "Injury Assistant": "M12 3v18M3 12h18M5.6 5.6l12.8 12.8m0-12.8L5.6 18.4",
    "Animal Bite Assistant": "M4 12c3-6 13-6 16 0M6 15c2 4 10 4 12 0M8 9v.1M16 9v.1",
    "Emergency Mode": "M12 3 2.5 20h19L12 3zM12 9v5M12 17h.01",
    "AI Companion": "M12 3a8 8 0 0 0-8 8v5a3 3 0 0 0 3 3h1v-7H7a5 5 0 0 1 10 0h-1v7h1a3 3 0 0 0 3-3v-5a8 8 0 0 0-8-8zM10 21h4",
    Wellbeing: "M20.8 8.6c0 5.4-8.8 11-8.8 11S3.2 14 3.2 8.6A4.6 4.6 0 0 1 12 6.5a4.6 4.6 0 0 1 8.8 2.1z",
    "FHIR / ABDM": "M4 4h16v16H4zM8 8h8M8 12h8M8 16h5",
    Settings: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM19 13.5l2-1.5-2-1.5-.5-2.3-2.5-.4L14.5 5 12 6l-2.5-1-1.5 2.8-2.5.4L5 10.5 3 12l2 1.5.5 2.3 2.5.4L9.5 19l2.5-1 2.5 1 1.5-2.8 2.5-.4z",
  };
  return <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] || paths.Dashboard} /></svg>;
}

function Field({ field, value, onChange }) {
  if (field.type === "file") return <label className={field.wide ? "field field-wide" : "field"} htmlFor={field.name}>
    <span>{field.label}</span><input id={field.name} name={field.name} type="file" accept={field.accept} capture={field.capture} onChange={(event) => onChange(field.name, event.target.files?.[0] || null)} />
  </label>;
  const common = {
    id: field.name, name: field.name, value: value ?? "", required: field.required,
    placeholder: field.placeholder || "", onChange: (event) => onChange(field.name, event.target.value),
  };
  return <label className={field.wide ? "field field-wide" : "field"} htmlFor={field.name}>
    <span>{field.label}{field.required && <i> *</i>}</span>
    {field.options ? <select {...common}><option value="">Select…</option>{field.options.map((option) => <option key={option} value={option}>{option}</option>)}</select>
      : field.multiline ? <textarea {...common} rows={field.rows || 3} />
        : <input {...common} type={field.type || "text"} min={field.min} max={field.max} step={field.step} />}
  </label>;
}

function DataList({ data, emptyText = "No information returned yet." }) {
  const items = asList(data);
  if (!items.length) return <div className="empty-state"><span className="empty-mark">○</span><p>{emptyText}</p></div>;
  return <div className="record-list">{items.map((item, index) => {
    const entries = item && typeof item === "object" ? Object.entries(item).filter(([, value]) => value !== null && typeof value !== "object") : [["Information", item]];
    const title = item?.name || item?.title || item?.test_name || item?.medicine_name || item?.document_type || item?.type || `Record ${index + 1}`;
    return <article className="record-card" key={item?.id ?? index}><div className="record-head"><strong>{String(title)}</strong><span className="record-date">{item?.date || item?.test_date || item?.created_at || ""}</span></div>
      <dl>{entries.filter(([key]) => !["id", "user_id", "name", "title", "test_name", "medicine_name", "document_type", "type"].includes(key)).map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{String(value)}</dd></div>)}</dl>
    </article>;
  })}</div>;
}

function EvidenceList({ evidence, question }) {
  if (!evidence?.length) return <p className="evidence-empty">No matching saved records were found for this answer.</p>;
  const queryTerms = [...new Set((question.match(/[\p{L}\p{N}]{2,}/gu) || []).slice(0, 12))];
  const matcher = queryTerms.length
    ? new RegExp(`(${queryTerms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "giu")
    : null;
  const detailsToShow = ["value", "unit", "reference_range", "status", "summary", "explanation", "description", "urgency", "notes", "message", "date", "source_date"];
  const emphasize = (value) => {
    const text = String(value).slice(0, 500);
    if (!matcher) return text;
    return text.split(matcher).map((part, index) => index % 2 === 1
      ? <mark key={`${part}-${index}`}>{part}</mark>
      : part);
  };
  return <div className="evidence-list">{evidence.map((item) => {
    const details = detailsToShow.filter((key) => item[key] !== null && item[key] !== undefined && item[key] !== "")
      .map((key) => [key, item[key]]);
    return <article className="evidence-card" key={`${item.source_type}-${item.source_id}`}>
      <div className="evidence-heading"><strong>{item.source_label || item.source_type}</strong><span>{String(item.source_type || "record").replaceAll("_", " ")} · #{item.source_id}</span></div>
      {details.length > 0 && <dl>{details.map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{emphasize(value)}</dd></div>)}</dl>}
    </article>;
  })}</div>;
}

function FormPanel({ title, description, fields, onSubmit, submitLabel = "Save record", busy = false, language = "en" }) {
  const [values, setValues] = useState({});
  const update = (key, value) => setValues((current) => ({ ...current, [key]: value }));
  return <form className="form-panel" onSubmit={async (event) => {
    event.preventDefault();
    const result = await onSubmit(values);
    if (result) setValues({});
  }}>
    <div className="form-heading"><div><h3>{title}</h3>{description && <p>{description}</p>}</div></div>
    <div className="fields-grid">{fields.map((field) => <Field key={field.name} field={{ ...field, label: translate(field.label, language) }} value={values[field.name]} onChange={update} />)}</div>
    <button className="button primary" disabled={busy} type="submit">{busy ? (language === "hi" ? "सहेजा जा रहा है…" : "Saving…") : translate(submitLabel, language)}<span aria-hidden="true">→</span></button>
  </form>;
}

const RESOURCE_FIELDS = {
  "Lab Results": [
    { name: "test_name", label: "Test name", required: true }, { name: "value", label: "Result value", required: true },
    { name: "unit", label: "Unit" }, { name: "reference_range", label: "Reference range" },
    { name: "status", label: "Status", options: ["unknown", "normal", "low", "high"] }, { name: "test_date", label: "Test date", type: "date" },
  ],
  Medicines: [
    { name: "name", label: "Medicine name", required: true }, { name: "strength", label: "Strength" },
    { name: "form", label: "Form (tablet, liquid, etc.)" }, { name: "dosage", label: "Dose instructions" },
    { name: "frequency", label: "How often" }, { name: "duration", label: "Duration" },
    { name: "start_date", label: "Start date", type: "date" }, { name: "end_date", label: "End date", type: "date" },
    { name: "notes", label: "Notes / instructions", multiline: true, wide: true },
  ],
  "Medical Records": [
    { name: "title", label: "Record title", required: true }, { name: "document_type", label: "Record type", required: true },
    { name: "source_date", label: "Document date", type: "date" },
    { name: "ocr_text", label: "Extracted text (optional)", multiline: true, wide: true },
    { name: "file", label: "Upload a PDF or clear image (PDF/JPEG/PNG/WebP)", type: "file", accept: ".pdf,image/jpeg,image/png,image/webp", wide: true },
  ],
  "Injury Assistant": [
    { name: "body_location", label: "Affected area", required: true },
    { name: "description", label: "Describe what happened and symptoms", multiline: true, wide: true, required: true },
    { name: "visible_findings", label: "Visible findings you observe", multiline: true, wide: true },
    { name: "image", label: "Optional injury photo for visual review", type: "file", accept: "image/*", capture: "environment", wide: true },
  ],
  "Animal Bite Assistant": [
    { name: "animal_type", label: "Animal, if known", required: true }, { name: "body_location", label: "Affected area" },
    { name: "description", label: "Describe the bite or scratch", multiline: true, wide: true, required: true },
    { name: "image", label: "Optional wound photo (do not approach the animal)", type: "file", accept: "image/*", capture: "environment", wide: true },
  ],
  "Emergency Mode": [
    { name: "event_type", label: "What is happening?", required: true },
    { name: "location", label: "Location (optional)" }, { name: "severity", label: "Severity", options: ["URGENT", "EMERGENCY", "LOW"] },
    { name: "description", label: "Additional details", multiline: true, wide: true },
  ],
  Wellbeing: [
    { name: "mood", label: "How are you feeling?", options: ["Very good", "Good", "Okay", "Low", "Very low"], required: true },
    { name: "stress_level", label: "Stress (1–10)", type: "number", min: 1, max: 10 },
    { name: "entry_date", label: "Date", type: "date" },
    { name: "message", label: "Anything else you'd like to note?", multiline: true, wide: true },
  ],
  "Doctor Visits": [
    { name: "doctor_name", label: "Clinician / clinic" }, { name: "visit_date", label: "Visit date", type: "date" },
    { name: "reason", label: "Reason for visit", multiline: true, wide: true },
    { name: "summary", label: "Visit notes", multiline: true, wide: true },
  ],
};

function ImageRecognitionCard({ title, endpoint, buttonLabel, helperText }) {
  const [image, setImage] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const analyze = async (event) => {
    event.preventDefault();
    if (!image) { setError("Choose or capture an image first."); return; }
    setBusy(true); setError(""); setResult(null);
    try {
      setResult(await api(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_data_url: await fileToDataUrl(image) }),
      }));
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  return <section className="surface recognition-card">
    <SectionHead title={title} subtitle={helperText} />
    <form onSubmit={analyze}>
      <label className="field" htmlFor={`image-${endpoint}`}><span>Image (capture or upload)</span>
        <input id={`image-${endpoint}`} type="file" accept="image/*" capture="environment" onChange={(event) => setImage(event.target.files?.[0] || null)} />
      </label>
      {image && <p className="hint">Selected file: {image.name}</p>}
      {error && <p className="inline-error" role="alert">{error}</p>}
      <button className="button secondary" type="submit" disabled={busy || !image}>{busy ? "Checking…" : buttonLabel}</button>
    </form>
    {result && <pre className="code-response">{JSON.stringify(result, null, 2)}</pre>}
  </section>;
}

function EmergencyTools({ userId }) {
  const [guidance, setGuidance] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [contact, setContact] = useState("");
  const [location, setLocation] = useState(null);
  const [places, setPlaces] = useState([]);
  const [share, setShare] = useState(null);
  const [newContact, setNewContact] = useState({ name: "", phone: "", contact_type: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    setError("");
    setContact("");
    setContacts([]);
    setLocation(null);
    setPlaces([]);
    setShare(null);
    setGuidance(null);

    const loadEmergencyData = async () => {
      try {
        const [guide, contactsResult] = await Promise.all([
          api("/api/emergency/guidance"),
          userId ? api(`/api/trusted-contacts?user_id=${encodeURIComponent(userId)}`) : Promise.resolve({ items: [] }),
        ]);
        if (!active) return;
        setGuidance(guide);
        setContacts(asList(contactsResult));
        setContact(String(contactsResult.items?.[0]?.id || ""));
      } catch (e) {
        if (active) setError(e.message);
      }
    };
    loadEmergencyData();
    return () => { active = false; };
  }, [userId]);

  const refreshContacts = async () => {
    const response = await api(`/api/trusted-contacts?user_id=${encodeURIComponent(userId)}`);
    setContacts(asList(response));
  };

  const addContact = async (event) => {
    event.preventDefault();
    setError(""); setNotice(""); setBusy(true);
    try {
      const created = await api("/api/trusted-contacts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...newContact, user_id: Number(userId) }),
      });
      await refreshContacts();
      setContact(String(created.id));
      setNewContact({ name: "", phone: "", contact_type: "" });
      setNotice("Trusted contact saved to this profile.");
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  const deleteContact = async (contactId) => {
    setError(""); setNotice(""); setBusy(true);
    try {
      await api(`/api/trusted-contacts/${encodeURIComponent(contactId)}`, { method: "DELETE" });
      await refreshContacts();
      if (String(contactId) === contact) setContact("");
      setNotice("Trusted contact removed.");
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  const findNearby = () => {
    setError("");
    setNotice("Update Coming Soon");
    setPlaces([]);
    setLocation(null);
  };

  const prepareShare = async () => {
    if (!location || !contact) { setError("Allow location access and choose a trusted contact first."); return; }
    setBusy(true); setError(""); setShare(null);
    try {
      const response = await api("/api/emergency/location-share/prepare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: Number(userId),
          contact_id: Number(contact),
          latitude: location.latitude,
          longitude: location.longitude,
        }),
      });
      setShare(response);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  const copyShare = async () => {
    try {
      await navigator.clipboard.writeText(share.message);
      setNotice("Message copied. It has not been sent; choose a messaging or calling app yourself.");
    } catch { setError("Clipboard access failed. Select and copy the message manually."); }
  };

  return <div className="emergency-tools">
    {error && <div className="alert error-alert" role="alert">{error}</div>}
    {notice && <div className="alert info-alert" role="status">{notice === "Update Coming Soon" ? <><strong>Update Coming Soon</strong><span>Nearby healthcare services will be available in a future update.</span></> : notice}</div>}
    <section className="surface">
      <SectionHead title="Emergency guidance" subtitle="General first-aid and warning information; not a substitute for dispatch or clinical advice." />
      {guidance ? <>
        <h3>Warning signs</h3><ul>{guidance.warning_signs?.map((item) => <li key={item}>{item}</li>)}</ul>
        <h3>Remote-area steps</h3><ol>{guidance.remote_area_steps?.map((item) => <li key={item}>{item}</li>)}</ol>
        <h3>Emergency bite kit</h3><ul>{guidance.bite_kit?.map((item) => <li key={item}>{item}</li>)}</ul>
        <p className="hint">{guidance.bite_guidance}</p>
      </> : <Loading />}
    </section>
    <section className="surface">
      <SectionHead title="Nearby healthcare" subtitle="Nearby healthcare services are temporarily unavailable." />
      <button className="button secondary" type="button" onClick={findNearby}>Use my location to find care</button>
      {places.length > 0 && <div className="record-list">{places.map((place, index) => <article className="record-card" key={`${place.latitude}-${place.longitude}-${index}`}>
        <div className="record-head"><strong>{place.name}</strong><span>{place.distance_km} km</span></div>
        <p>{place.type}{place.address ? ` · ${place.address}` : ""}</p>
        <div className="place-links"><a href={place.map_url} target="_blank" rel="noreferrer">Map</a><a href={place.directions_url} target="_blank" rel="noreferrer">Directions</a></div>
      </article>)}</div>}
      {location && !busy && places.length === 0 && <div className="empty-state"><p>No nearby facilities were returned. Contact local emergency services if this is urgent.</p></div>}
      {location && <p className="hint">Location is held in this page session for the requested search and share preparation.</p>}
    </section>
    {userId && <section className="surface">
      <SectionHead title="Trusted contacts" subtitle="Add a person you choose. No messages are sent by this application." />
      <form className="fields-grid" onSubmit={addContact}>
        <label className="field"><span>Name</span><input required value={newContact.name} onChange={(event) => setNewContact((current) => ({ ...current, name: event.target.value }))} /></label>
        <label className="field"><span>Phone</span><input type="tel" value={newContact.phone} onChange={(event) => setNewContact((current) => ({ ...current, phone: event.target.value }))} /></label>
        <label className="field"><span>Relationship</span><input value={newContact.contact_type} onChange={(event) => setNewContact((current) => ({ ...current, contact_type: event.target.value }))} /></label>
        <button className="button primary" type="submit" disabled={busy}>Save trusted contact</button>
      </form>
      {contacts.map((item) => <div className="contact-row" key={item.id}><span><strong>{item.name}</strong><small>{item.phone || "No phone number"}{item.contact_type ? ` · ${item.contact_type}` : ""}</small></span><button className="text-button" type="button" disabled={busy} onClick={() => deleteContact(item.id)}>Remove</button></div>)}
      <label className="field" htmlFor="share-contact"><span>Prepare location message for</span><select id="share-contact" value={contact} onChange={(event) => setContact(event.target.value)}><option value="">Select a trusted contact</option>{contacts.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
      <button className="button secondary" type="button" disabled={busy || !contact || !location} onClick={prepareShare}>Prepare location message</button>
      {share && <div className="response-box"><p>{share.notice}</p><pre>{share.message}</pre><button className="button secondary" type="button" onClick={copyShare}>Copy message</button>{share.contact?.phone && <a className="button secondary" href={`tel:${encodeURIComponent(share.contact.phone)}`}>Call contact</a>}</div>}
    </section>}
  </div>;
}

export default function App() {
  const [page, setPage] = useState("Dashboard");
  const [users, setUsers] = useState([]);
  const [userId, setUserId] = useState(localStorage.getItem("health-copilot-user") || "");
  const [profile, setProfile] = useState(null);
  const [pageData, setPageData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [userForm, setUserForm] = useState({ name: "", email: "", phone: "" });
  const [question, setQuestion] = useState("");
  const [chatResponse, setChatResponse] = useState(null);
  const [wellbeingMessage, setWellbeingMessage] = useState("");
  const [wellbeingResponse, setWellbeingResponse] = useState(null);
  const [doctorSummary, setDoctorSummary] = useState(null);
  const [selectedCandidates, setSelectedCandidates] = useState([]);
  const [assistantResponse, setAssistantResponse] = useState(null);
  const [connectedData, setConnectedData] = useState({});
  const [apiBase, setApiBase] = useState(API_BASE);
  const [language, setLanguage] = useState(localStorage.getItem("health-copilot-language") || "en");

  const activeUser = useMemo(() => users.find((user) => String(user.id) === String(userId)), [users, userId]);
  const request = useCallback(async (path, options) => api(path, options), []);
  const loadUsers = useCallback(async () => {
    try {
      const data = await request("/api/users");
      const list = asList(data);
      setUsers(list);
      if (!userId && list[0]?.id !== undefined) setUserId(String(list[0].id));
    } catch (e) { setError(`Could not load users: ${e.message}`); }
  }, [request, userId]);

  useEffect(() => { loadUsers(); }, [loadUsers]);
  useEffect(() => {
    if (userId) localStorage.setItem("health-copilot-user", userId);
    else localStorage.removeItem("health-copilot-user");
  }, [userId]);
  useEffect(() => {
    localStorage.setItem("health-copilot-language", language);
    document.documentElement.lang = language;
  }, [language]);

  const loadPage = useCallback(async (target = page) => {
    setError(""); setLoading(true); setPageData(null);
    try {
      if (target === "Dashboard") {
        if (!userId) throw new Error("Select or create a user to load their dashboard.");
        const [profileResult, docs, labs, meds, timeline] = await Promise.all([
          request(`/api/health-profile/${encodeURIComponent(userId)}`),
          request(toPath("/api/medical-documents", userId)),
          request(toPath("/api/lab-results", userId)),
          request(toPath("/api/medicines", userId)),
          request(`/api/timeline/${encodeURIComponent(userId)}`),
        ]);
        setProfile(profileResult);
        setPageData({ docs, labs, meds, timeline });
      } else if (target === "Health Timeline" && userId) {
        setPageData(await request(`/api/timeline/${encodeURIComponent(userId)}`));
      } else if (target === "Health Profile" && userId) {
        setProfile(await request(`/api/health-profile/${encodeURIComponent(userId)}`));
      } else if (target === "FHIR / ABDM" && userId) {
        setPageData(null);
      } else if (ROUTES[target]) {
        if (!userId) throw new Error("Select or create a user before loading health information.");
        const data = await request(toPath(ROUTES[target], userId));
        if (target === "Lab Results") {
          const trends = await request(`/api/lab-results/${encodeURIComponent(userId)}/trends`);
          setPageData({ records: data, trends });
        } else {
          setPageData(data);
        }
      }
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, [page, request, userId]);

  useEffect(() => { loadPage(page); }, [page, userId, loadPage]);

  const saveResource = async (target, values) => {
    setSaving(true); setError(""); setNotice("");
    try {
      const fields = Object.fromEntries(Object.entries(values).filter(([, value]) => value !== "" && value !== null && value !== undefined));
      fields.user_id = Number(userId);
      const file = fields.file;
      const image = fields.image;
      delete fields.file;
      delete fields.image;
      let data;
      if (target === "Medical Records" && file) {
        const formData = new FormData();
        formData.append("file", file);
        Object.entries(fields).forEach(([key, value]) => { if (value !== "" && key !== "ocr_text") formData.append(key, value); });
        data = await request("/api/medical-documents/upload", { method: "POST", body: formData });
      } else if (target === "Injury Assistant") {
        const injury = {
          user_id: fields.user_id,
          body_location: fields.body_location,
          description: fields.description,
          visible_findings: fields.visible_findings || null,
        };
        data = await request("/api/injuries", {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(injury),
        });
        if (image) {
          const analysis = await request("/api/injuries/analyze", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image_data_url: await fileToDataUrl(image), body_location: fields.body_location, description: fields.description }),
          });
          setAssistantResponse(analysis);
        } else {
          setAssistantResponse({ record: data, note: "No image was supplied; no visual assessment was attempted. The recorded first-aid and warning guidance is general." });
        }
      } else if (target === "Animal Bite Assistant") {
        const bite = {
          user_id: fields.user_id,
          animal_type: fields.animal_type,
          body_location: fields.body_location || null,
          description: fields.description,
        };
        data = await request("/api/animal-bites", {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(bite),
        });
        if (image) {
          const analysis = await request("/api/animal-bites/analyze", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image_data_url: await fileToDataUrl(image), animal_type: fields.animal_type, body_location: fields.body_location, description: fields.description }),
          });
          setAssistantResponse(analysis);
        } else {
          setAssistantResponse({ record: data, note: "No image was supplied; no visual assessment was attempted. Seek prompt professional assessment after a bite." });
        }
      } else {
        if (target === "Wellbeing" && fields.stress_level !== undefined) {
          fields.stress_level = Number(fields.stress_level);
        } else if (target === "Lab Results" && fields.value !== undefined) {
          fields.value = Number(fields.value);
        }
        data = await request(ROUTES[target], {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(fields),
        });
      }
      if (target === "Injury Assistant" || target === "Animal Bite Assistant") {
        setNotice("The report was saved. Guidance is informational and is not a diagnosis.");
      } else {
        setNotice(data?.message || "Saved successfully.");
      }
      await loadPage(page);
      return true;
    } catch (e) { setError(e.message); return false; }
    finally { setSaving(false); }
  };

  const createUser = async (event) => {
    event.preventDefault(); setSaving(true); setError(""); setNotice("");
    try {
      const created = await request("/api/users", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(userForm),
      });
      await loadUsers();
      const newId = created?.id ?? created?.user?.id;
      if (newId !== undefined) setUserId(String(newId));
      setUserForm({ name: "", email: "", phone: "" });
      setNotice("User created.");
    } catch (e) { setError(`Could not create user: ${e.message}`); }
    finally { setSaving(false); }
  };

  const askQuestion = async (event) => {
    event.preventDefault(); setError(""); setNotice(""); setChatResponse(null); setSaving(true);
    try {
      const data = await request("/api/health-chat", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: Number(userId), question, response_language: language }),
      });
      setChatResponse(data);
    } catch (e) { setError(e.message); }
    finally { setSaving(false); }
  };

  const fetchConnected = async (kind) => {
    if (!userId) { setError("Select or create a user first."); return; }
    setError(""); setSaving(true);
    try {
      const endpoint = kind === "FHIR patient" ? `/api/fhir/patient/${encodeURIComponent(userId)}`
        : kind === "FHIR bundle" ? `/api/fhir/bundle/${encodeURIComponent(userId)}`
          : `/api/abdm/mock/${encodeURIComponent(userId)}`;
      const data = await request(endpoint);
      setConnectedData((current) => ({ ...current, [kind]: data }));
    } catch (e) { setError(`${kind}: ${e.message}`); }
    finally { setSaving(false); }
  };

  const analyzeDocument = async (record) => {
    if (!record?.id) { setError("This record has no ID, so it cannot be sent for analysis."); return; }
    setError(""); setNotice(""); setSaving(true);
    try {
      const result = await request(`/api/medical-documents/${encodeURIComponent(record.id)}/analyze`, { method: "POST" });
      setNotice("Text and possible lab values extracted. Review them against the original report before confirming.");
      setSelectedCandidates([]);
      setConnectedData((current) => ({ ...current, analysis: result }));
    } catch (e) { setError(e.message); }
    finally { setSaving(false); }
  };

  const confirmDocumentResults = async () => {
    const analysis = connectedData.analysis;
    if (!analysis?.document_id || selectedCandidates.length === 0) return;
    setError(""); setSaving(true);
    try {
      const result = await request(`/api/medical-documents/${encodeURIComponent(analysis.document_id)}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: Number(userId), candidate_indices: selectedCandidates }),
      });
      setNotice(`${result.confirmed_results.length} selected result(s) added to your lab history.`);
      setConnectedData((current) => ({ ...current, analysis: null }));
      await loadPage("Medical Records");
    } catch (e) { setError(e.message); }
    finally { setSaving(false); }
  };

  const createDoctorSummary = async () => {
    if (!userId) return;
    setError(""); setSaving(true); setDoctorSummary(null);
    try {
      const result = await request("/api/doctor-visits/summary", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: Number(userId) }),
      });
      setDoctorSummary(result);
    } catch (e) { setError(e.message); }
    finally { setSaving(false); }
  };

  const sendWellbeingMessage = async (event) => {
    event.preventDefault(); setError(""); setSaving(true); setWellbeingResponse(null);
    try {
      const result = await request("/api/wellbeing/response", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: wellbeingMessage, language }),
      });
      setWellbeingResponse(result);
    } catch (e) { setError(e.message); }
    finally { setSaving(false); }
  };

  const docItems = asList(pageData);
  const setCurrentPage = (target) => { setNotice(""); setError(""); setPage(target); window.scrollTo({ top: 0, behavior: "smooth" }); };
  const pageMeta = PAGE_META[page];
  const meta = [translate(pageMeta[0], language), translate(pageMeta[1], language)];

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#dashboard" onClick={(event) => { event.preventDefault(); setCurrentPage("Dashboard"); }}>
        <span className="brand-icon"><Icon name="Health Profile" /></span><span><strong>care<span>compass</span></strong><small>YOUR HEALTH, CONNECTED</small></span>
      </a>
      <div className="user-switch">
        <label htmlFor="active-user">ACTIVE PROFILE</label>
        <select id="active-user" value={userId} onChange={(event) => setUserId(event.target.value)}>
          <option value="">Select a user</option>
          {users.map((user) => <option value={user.id} key={user.id}>{user.name || user.full_name || `User ${user.id}`}</option>)}
        </select>
      </div>
      <nav className="nav" aria-label="Main navigation">
        {NAV_GROUPS.map((group) => <div className="nav-group" key={group.label}><p>{translate(group.label, language)}</p>{group.items.map((item) =>
          <button key={item} type="button" onClick={() => setCurrentPage(item)} className={`nav-item ${page === item ? "active" : ""}`}>
            <Icon name={item} /><span>{translate(item, language)}</span>{page === item && <span className="nav-active-dot" />}
          </button>)}</div>)}
      </nav>
      <div className="sidebar-footer"><span className="status-dot neutral-dot" /> API endpoint <span className="api-host">{API_BASE.replace(/^https?:\/\//, "")}</span></div>
    </aside>

    <main className="main-panel">
      <header className="topbar">
        <div className="breadcrumbs"><span>CareCompass</span><b>/</b><strong>{translate(page, language)}</strong></div>
        <div className="top-actions"><label className="language-select" htmlFor="ui-language"><span className="sr-only">Language</span><select id="ui-language" value={language} onChange={(event) => setLanguage(event.target.value)}><option value="en">EN</option><option value="hi">हिंदी</option></select></label><span className="connection-pill"><span className="status-dot neutral-dot" /> API endpoint</span>
          <button className="avatar" type="button" onClick={() => setCurrentPage("Settings")} aria-label="Open settings">{activeUser?.name?.[0]?.toUpperCase() || "U"}</button>
        </div>
      </header>
      <div className="page-content">
        <section className="page-heading"><div><p className="eyebrow">CARECOMPASS <span>·</span> {translate(page, language).toUpperCase()}</p><h1>{meta[0]}</h1><p>{meta[1]}</p></div>
          {page !== "Settings" && <button className="button secondary refresh-btn" onClick={() => { setNotice(""); loadPage(page); }} disabled={loading}><span>↻</span> {translate("Refresh", language)}</button>}
        </section>
        {error && <div className="alert error-alert" role="alert"><strong>Something needs attention</strong><span>{error}</span><button type="button" onClick={() => setError("")} aria-label="Dismiss error">×</button></div>}
        {notice && <div className="alert success-alert" role="status"><span>✓</span>{notice}<button type="button" onClick={() => setNotice("")} aria-label="Dismiss message">×</button></div>}
        {!userId && page !== "Settings" && <div className="alert info-alert"><strong>No active user</strong><span>Create or select a profile in Settings to connect health information.</span><button className="text-button" onClick={() => setCurrentPage("Settings")}>Go to settings →</button></div>}

        {page === "Dashboard" && <Dashboard profile={profile} data={pageData} loading={loading} onNavigate={setCurrentPage} />}
        {page === "Health Timeline" && <section className="surface"><SectionHead title="Events" subtitle="Events returned for this profile" /><DataList data={pageData} emptyText={loading ? "Loading timeline…" : "No timeline events returned."} /></section>}
        {page === "Health Profile" && <section className="surface"><SectionHead title="Profile details" subtitle="Profile data received from the API" /><ProfileView profile={profile} loading={loading} /></section>}

        {ROUTES[page] && <div className={`split-layout ${page === "Injury Assistant" || page === "Animal Bite Assistant" ? "assistant-layout" : ""}`}>
          <section className="surface"><SectionHead title={page === "Medical Records" ? "Your records" : page} subtitle={`Information currently returned for ${activeUser?.name || "the selected profile"}`} />
            {loading ? <Loading /> : page === "Lab Results" ? <DataList data={pageData?.records} emptyText="No lab results returned for this profile." /> : <DataList data={pageData} emptyText={`No ${page.toLowerCase()} returned for this profile.`} />}
            {page === "Medical Records" && !loading && docItems.map((record) => <button className="button secondary analyze-button" key={record.id} disabled={saving || !record.id} onClick={() => analyzeDocument(record)}>Request analysis for {record.title || record.document_type || `record ${record.id}`} →</button>)}
            {page === "Medical Records" && connectedData.analysis && <div className="response-box"><div className="response-label">EXTRACTED CANDIDATES — REVIEW BEFORE SAVING</div>
              <p>OCR may misread values. Compare every item against the original report; selected values become part of the health record.</p>
              {(connectedData.analysis.processing?.detected_tests || []).map((candidate, index) => <label className="candidate-row" key={`${candidate.name}-${index}`}>
                <input type="checkbox" checked={selectedCandidates.includes(index)} onChange={(event) => setSelectedCandidates((current) => event.target.checked ? [...current, index] : current.filter((selected) => selected !== index))} />
                <span><strong>{candidate.name}: {candidate.value} {candidate.unit}</strong><small>Reference: {candidate.reference_range || "not present"} · Status: {candidate.status} · Source: {candidate.source_text}</small></span>
              </label>)}
              {connectedData.analysis.explanation?.summary && <p>{connectedData.analysis.explanation.summary}</p>}
              <button className="button primary" disabled={saving || !selectedCandidates.length} onClick={confirmDocumentResults}>Confirm selected lab values</button>
            </div>}
          </section>
          <FormPanel title={page === "Injury Assistant" || page === "Animal Bite Assistant" ? "Tell us what happened" : page === "Medical Records" ? "Add a record" : `Add ${page === "Lab Results" ? "result" : page === "Medicines" ? "medicine" : "check-in"}`}
            description={page === "Medical Records" ? "Files are stored on the backend, but authentication and access controls are not implemented. Images use bilingual OCR when Tesseract English and Hindi data are installed." : page.includes("Assistant") ? "Image review is optional and may be unavailable unless OmniRoute vision is configured. Never delay urgent care." : ""}
            fields={RESOURCE_FIELDS[page] || []} onSubmit={(values) => saveResource(page, values)} busy={saving} submitLabel={page.includes("Assistant") ? "Submit for guidance" : page === "Doctor Visits" ? "Save visit" : "Save"} language={language} />
          {(page === "Injury Assistant" || page === "Animal Bite Assistant") && assistantResponse && <section className="surface assistant-response"><SectionHead title="Service response" subtitle="Response returned by the connected endpoint" /><pre className="code-response">{JSON.stringify(assistantResponse, null, 2)}</pre></section>}
          {page === "Lab Results" && <section className="surface trend-panel"><SectionHead title="Lab trends" subtitle="Descriptive changes from saved results with matching test names and units; not clinical interpretation." />
            {pageData?.trends?.items?.length ? pageData.trends.items.map((trend) => <article className="trend-card" key={trend.test_name}><div className="record-head"><strong>{trend.test_name}</strong><span>{trend.direction}</span></div><p>{trend.change === null ? "More comparable results are needed to show a numeric change." : `Change: ${trend.change} ${trend.unit || ""}`}</p><p>{trend.interpretation}</p><DataList data={trend.values} emptyText="No values." /></article>) : <p className="hint">No saved lab results are available for trend comparison.</p>}
          </section>}
          {page === "Medicines" && <ImageRecognitionCard title="Recognize a medicine package" endpoint="/api/medicines/recognize" buttonLabel="Request image recognition" helperText="Recognition may be uncertain. It does not add a medicine to your record; verify the package with a pharmacist before recording or taking it." />}
          {page === "Animal Bite Assistant" && <ImageRecognitionCard title="Optional animal identification" endpoint="/api/animal-bites/recognize-animal" buttonLabel="Request animal identification" helperText="Keep away from animals. A picture-based label is uncertain and cannot estimate rabies exposure." />}
          {page === "Doctor Visits" && <section className="surface"><SectionHead title="Visit preparation summary" subtitle="Drafted only from saved records; verify details before sharing." />
            <button className="button secondary" type="button" onClick={createDoctorSummary} disabled={saving || !userId}>{saving ? "Preparing…" : "Prepare clinician summary"}</button>
            {doctorSummary && <pre className="code-response">{JSON.stringify(doctorSummary, null, 2)}</pre>}
          </section>}
        </div>}

        {page === "Emergency Mode" && <div className="emergency-layout">
          <section className="emergency-callout"><div className="emergency-icon">!</div><div><p className="card-kicker">IMMEDIATE HELP</p><h2>Need urgent medical help?</h2><p>This app cannot contact emergency services or assess an emergency. Call your local emergency number now if you or someone else is in immediate danger.</p></div></section>
          <EmergencyTools userId={userId} />
          <div className="split-layout"><section className="surface"><SectionHead title="Recorded events" subtitle="Emergency events returned for this profile" />{loading ? <Loading /> : <DataList data={pageData} emptyText="No emergency events returned." />}</section>
            <FormPanel title="Record an event" fields={RESOURCE_FIELDS["Emergency Mode"]} onSubmit={(values) => saveResource("Emergency Mode", values)} busy={saving} submitLabel="Save event" language={language} /></div>
        </div>}

        {page === "AI Companion" && <div className="chat-layout"><section className="chat-intro"><div className="chat-orb"><Icon name="AI Companion" /></div><h2>A thoughtful space for your health questions.</h2><p>Responses come from the connected health service. They may be incomplete; this companion does not diagnose or replace advice from a qualified professional.</p></section>
          <section className="surface chat-panel"><SectionHead title="Ask a question" subtitle="Your question is sent to the health-chat API." />
            <form onSubmit={askQuestion}><label className="field" htmlFor="health-question"><span>Your question</span><textarea id="health-question" value={question} onChange={(event) => setQuestion(event.target.value)} rows="3" required placeholder="What would you like to understand about your health information?" /></label><button className="button primary" disabled={saving || !userId}>{saving ? "Sending…" : "Send question →"}</button></form>
            {chatResponse && <div className="response-box">
              <div className="response-label">RECORD-GROUNDED RESPONSE · {chatResponse.ai_status || "service response"}</div>
              <p className="chat-answer">{chatResponse.answer}</p>
              <h3 className="evidence-title">Supporting records</h3>
              <p className="evidence-caption">Highlighted words match your question. These are retrieved records, not an independent clinical interpretation.</p>
              <EvidenceList evidence={chatResponse.evidence} question={question} />
            </div>}
          </section>
        </div>}

        {page === "Wellbeing" && <section className="surface wellbeing-response-panel">
          <SectionHead title="Supportive conversation" subtitle="Share only what you are comfortable sharing. This companion is not a therapist and cannot respond to emergencies." />
          <form onSubmit={sendWellbeingMessage}>
            <label className="field" htmlFor="wellbeing-message"><span>What is on your mind?</span><textarea id="wellbeing-message" value={wellbeingMessage} onChange={(event) => setWellbeingMessage(event.target.value)} rows="4" maxLength="4000" required /></label>
            <button className="button secondary" disabled={saving || !userId}>{saving ? "Sending…" : "Ask for supportive guidance"}</button>
          </form>
          {wellbeingResponse && <div className={`response-box ${wellbeingResponse.crisis_escalation ? "crisis-box" : ""}`} role="status"><strong>{wellbeingResponse.crisis_escalation ? "Immediate support" : "Supportive response"}</strong><p>{wellbeingResponse.response}</p>{wellbeingResponse.activities?.map((activity) => <p key={activity}>{activity}</p>)}{wellbeingResponse.safety_note && <small>{wellbeingResponse.safety_note}</small>}</div>}
        </section>}

        {page === "FHIR / ABDM" && <div className="connected-grid">
          {[["FHIR patient", "Request patient resource", "Patient"], ["FHIR bundle", "Request resource bundle", "Bundle"], ["ABDM mock", "Request ABDM mock response", "ABDM"]].map(([key, label, eyebrow]) =>
            <section className="surface connected-card" key={key}><div className="connected-icon"><Icon name="FHIR / ABDM" /></div><p className="card-kicker">{eyebrow}</p><h3>{label}</h3><p>Data is fetched from the connected backend for the active profile.</p><button className="button secondary" onClick={() => fetchConnected(key)} disabled={saving || !userId}>{saving ? "Requesting…" : "Fetch data →"}</button>
              {connectedData[key] !== undefined && <pre className="code-response">{JSON.stringify(connectedData[key], null, 2)}</pre>}
            </section>)}
        </div>}

        {page === "Settings" && <div className="settings-grid">
          <section className="surface"><SectionHead title="User profiles" subtitle="Profiles are loaded from the users API." />
            <div className="settings-user-row"><label className="field" htmlFor="settings-user"><span>Active user</span><select id="settings-user" value={userId} onChange={(event) => setUserId(event.target.value)}><option value="">Select a user</option>{users.map((user) => <option value={user.id} key={user.id}>{user.name || user.full_name || `User ${user.id}`}</option>)}</select></label><button className="button secondary" onClick={loadUsers} disabled={loading}>Reload users</button></div>
            <div className="divider" /><h3 className="form-title">Create a profile</h3>
            <form onSubmit={createUser} className="fields-grid user-create">
              {[["name", "Full name", "text"], ["email", "Email address", "email"], ["phone", "Phone number", "tel"]].map(([key, label, type]) => <label className="field" key={key} htmlFor={`new-${key}`}><span>{label}{key === "name" && <i> *</i>}</span><input id={`new-${key}`} type={type} required={key === "name"} value={userForm[key]} onChange={(event) => setUserForm((current) => ({ ...current, [key]: event.target.value }))} /></label>)}
              <button className="button primary" disabled={saving}>Create user →</button>
            </form>
          </section>
          <section className="surface"><SectionHead title="API connection" subtitle="Configure the backend origin for this browser session." />
            <p className="error-banner">This scaffold has no sign-in or access controls. Do not enter real health information or expose it to the public internet. When configured, OmniRoute receives only the health text or image required for the requested AI feature.</p>
            <label className="field" htmlFor="api-base"><span>VITE_API_BASE_URL</span><input id="api-base" value={apiBase} onChange={(event) => setApiBase(event.target.value)} /></label>
            <p className="hint">The application uses the build-time VITE_API_BASE_URL environment variable (default: http://localhost:8000). Changing this field previews the value only; configure the environment and rebuild to apply it. Interface translation is partial; stored medical records are not automatically translated.</p>
            <div className="connection-detail"><span className="status-dot" /><span>Current API origin</span><code>{API_BASE}</code></div>
          </section>
        </div>}
        <footer className="page-footer"><span>CareCompass · Records are linked to the selected profile; API ownership controls are not implemented.</span><span>AI requests may transmit supplied health text or images to your configured OmniRoute provider. This app is not emergency care.</span></footer>
      </div>
    </main>
  </div>;
}

function SectionHead({ title, subtitle }) {
  return <div className="section-head"><div><h2>{title}</h2><p>{subtitle}</p></div><span className="section-mark">✳</span></div>;
}

function Loading() {
  return <div className="loading-state"><span className="spinner" /> Loading from the health service…</div>;
}

function ProfileView({ profile, loading }) {
  if (loading) return <Loading />;
  if (!profile) return <div className="empty-state"><p>No profile information returned.</p></div>;
  const user = profile.user || {};
  const sections = [
    ["Medical records", "documents"], ["Lab results", "lab_results"], ["Medicines", "medicines"],
    ["Diagnoses", "diagnoses"], ["Doctor visits", "doctor_visits"], ["Injuries", "injuries"],
    ["Animal bites", "animal_bites"], ["Emergency events", "emergency_events"],
    ["Wellbeing", "wellbeing"], ["Trusted contacts", "trusted_contacts"],
  ];
  return <div className="profile-view">
    <section className="profile-identity"><span className="card-kicker">HEALTH PROFILE</span><h2>{user.name || "Unnamed profile"}</h2>
      <dl>{Object.entries(user).filter(([key, value]) => key !== "id" && value !== null && value !== "").map(([key, value]) =>
        <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{String(value)}</dd></div>)}</dl>
    </section>
    <div className="profile-sections">{sections.map(([title, key]) =>
      <section className="surface profile-section" key={key}><SectionHead title={title} subtitle={`${asList(profile[key]).length} saved record(s)`} />
        <DataList data={profile[key]} emptyText={`No ${title.toLowerCase()} on this profile.`} />
      </section>)}
    </div>
  </div>;
}

function Dashboard({ profile, data, loading, onNavigate }) {
  const count = (value) => asList(value).length;
  const user = profile?.user || profile?.profile || {};
  const metrics = [
    ["Medical records", count(data?.docs), "Medical Records", "◫"],
    ["Lab results", count(data?.labs), "Lab Results", "⌁"],
    ["Medicines", count(data?.meds), "Medicines", "✚"],
    ["Timeline events", count(data?.timeline), "Health Timeline", "↗"],
  ];
  return <div className="dashboard-content">
    <section className="welcome-card"><div className="welcome-decoration"><span>✳</span><span>+</span><span>○</span></div><div className="welcome-copy"><p className="card-kicker">YOUR PERSONAL HEALTH SPACE</p><h2>{user.name || user.full_name ? `Welcome, ${user.name || user.full_name}` : "Welcome to your health space"}</h2><p>Your connected health information, brought together in one place.</p><button className="button white-button" type="button" onClick={() => onNavigate("Health Profile")}>View health profile <span>→</span></button></div><div className="welcome-art" aria-hidden="true"><div className="art-ring ring-one" /><div className="art-ring ring-two" /><div className="art-plus">+</div><div className="art-core">✚</div><div className="art-dot dot-a" /><div className="art-dot dot-b" /></div></section>
    <div className="metric-grid">{metrics.map(([label, value, destination, icon]) => <button className="metric-card" type="button" key={label} onClick={() => onNavigate(destination)}><span className="metric-icon">{icon}</span><span className="metric-label">{label}</span><strong>{loading ? "—" : value}</strong><span className="metric-link">View details <b>→</b></span></button>)}</div>
    <div className="dashboard-columns">
      <section className="surface quick-actions"><SectionHead title="Quick access" subtitle="Continue with a health task" />
        <div className="quick-list">{[["Medical Records", "Add a document or note"], ["Lab Results", "Review or add a result"], ["Wellbeing", "Record a check-in"], ["AI Companion", "Ask a health question"]].map(([title, caption]) =>
          <button key={title} type="button" onClick={() => onNavigate(title)}><span className="quick-icon"><Icon name={title} /></span><span><strong>{title}</strong><small>{caption}</small></span><b>→</b></button>)}</div>
      </section>
      <section className="emergency-mini"><span className="mini-alert-icon">!</span><p className="card-kicker">NEED HELP NOW?</p><h2>Urgent care information</h2><p>If this is an emergency, call your local emergency number. This app cannot contact emergency services.</p><button className="button emergency-button" onClick={() => onNavigate("Emergency Mode")}>Open emergency mode →</button></section>
    </div>
    <section className="surface dashboard-recent"><SectionHead title="Recently connected records" subtitle="Records returned by the health service" /><div className="recent-columns">{[["Medical records", data?.docs], ["Lab results", data?.labs]].map(([label, items]) => <div key={label}><h3>{label}</h3>{loading ? <Loading /> : <DataList data={items} emptyText="Nothing returned yet." />}</div>)}</div></section>
  </div>;
}
