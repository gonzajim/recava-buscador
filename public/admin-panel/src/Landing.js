import React from 'react';
import {
ShieldCheck,
Search,
Scale,
FileCheck,
BarChart3,
Clock,
ArrowRight,
CheckCircle2,
Lock,
Briefcase,
Users,
ClipboardCheck
} from 'lucide-react';

const Landing = ({ onLoginClick }) => {
const features = [
{
title: "Rigor Jurídico y Financiero",
desc: "Análisis exhaustivo basado exclusivamente en el texto del informe, eliminando riesgos de interpretación errónea.",
icon:
<Scale className="w-6 h-6 text-blue-600" />
},
{
title: "Criterios Personalizables",
desc: "Adapte la auditoría a sus propios estándares cargando sus matrices de indicadores específicas.",
icon:
<ClipboardCheck className="w-6 h-6 text-indigo-600" />
},
{
title: "Evidencia Documental Directa",
desc: "Cada hallazgo incluye la ubicación exacta y el párrafo literal para una verificación inmediata.",
icon:
<Search className="w-6 h-6 text-emerald-600" />
},
{
title: "Supervisión Experta",
desc: "Diseñado como un asistente de alto nivel: la IA propone y el experto valida los resultados finales.",
icon:
<Users className="w-6 h-6 text-amber-600" />
}
];

const valueProps = [
{
label: "Garantía Anti-Extrapolación",
desc: "La IA tiene prohibido inventar datos; si no está en el documento, se marca como omitido."
},
{
label: "Actualización Normativa",
desc: "El sistema integra el corpus legal de NEIS S1 y CSRD actualizado semanalmente."
},
{
label: "Integridad Histórica",
desc: "Snapshots inmutables de cada auditoría para garantizar la trazabilidad en el tiempo."
}
];

return (
<div className="min-h-screen bg-slate-50 font-sans text-slate-900">
    {/* Navegación */}
    <nav className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
            <div className="flex items-center gap-3">
                <div className="bg-blue-700 p-2 rounded-lg shadow-blue-200 shadow-lg">
                    <ShieldCheck className="text-white w-6 h-6" />
                </div>
                <div>
                    <span className="font-bold text-xl block leading-none text-slate-900">RECAVA</span>
                    <span className="text-xs font-semibold text-blue-600 tracking-widest uppercase">Auditoría AI</span>
                </div>
            </div>
            <div className="hidden md:flex gap-10 text-sm font-semibold text-slate-600">
                <a href="#metodologia" className="hover:text-blue-700 transition-colors">Metodología</a>
                <a href="#beneficios" className="hover:text-blue-700 transition-colors">Beneficios</a>
            </div>
            <button
                onClick={onLoginClick}
                className="bg-blue-700 text-white px-6 py-2.5 rounded-lg text-sm font-bold hover:bg-blue-800 transition-all shadow-md hover:shadow-xl flex items-center gap-2">
                Iniciar Auditoría
                <ArrowRight className="w-4 h-4" />
            </button>
        </div>
    </nav>

    {/* Hero Section para Perfil Ejecutivo */}
    <section className="relative pt-24 pb-20 overflow-hidden bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
            <div
                className="inline-flex items-center gap-2 bg-blue-50 border border-blue-100 px-4 py-1.5 rounded-full text-blue-700 text-xs font-bold mb-8 tracking-wide">
                <Lock className="w-3 h-3" /> TECNOLOGÍA DE AUDITORÍA CERTIFICADA (V3.1)
            </div>
            <h1 className="text-4xl md:text-6xl font-black text-slate-900 mb-8 leading-[1.15]">
                Auditoría Inteligente de Sostenibilidad <br />
                <span className="text-blue-700">con Rigor Legal y Financiero</span>
            </h1>
            <p className="text-xl text-slate-600 mb-12 max-w-3xl mx-auto leading-relaxed">
                Optimice la revisión de informes NEIS y CSRD. Nuestra IA especializada actúa como un analista senior,
                extrayendo evidencias precisas y verificables para su validación final.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
                {valueProps.map((item, i) => (
                <div key={i} className="bg-slate-50 p-6 rounded-2xl border border-slate-100 text-left">
                    <h4 className="font-bold text-slate-900 mb-2 flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-blue-600" /> {item.label}
                    </h4>
                    <p className="text-sm text-slate-500 leading-snug">{item.desc}</p>
                </div>
                ))}
            </div>
        </div>

        {/* Elemento Decorativo Elegante */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full opacity-5 pointer-events-none">
            <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-blue-600 rounded-full blur-[150px]"></div>
        </div>
    </section>

    {/* Metodología de Trabajo */}
    <section id="metodologia" className="py-24 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col md:flex-row items-end justify-between mb-16 gap-6">
                <div className="max-w-2xl">
                    <h2 className="text-3xl font-bold text-slate-900 mb-4">¿Cómo funciona Recava Auditor?</h2>
                    <p className="text-slate-500 text-lg">Un proceso estructurado para garantizar la máxima fiabilidad
                        en la extracción de información no financiera.</p>
                </div>
                <div
                    className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 inline-flex items-center gap-4 text-sm font-bold text-slate-700">
                    <Clock className="text-blue-600 w-5 h-5" /> Análisis instantáneo vs. Semanas de trabajo manual
                </div>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
                {features.map((f, i) => (
                <div key={i}
                    className="group bg-white p-8 rounded-3xl border border-slate-200 hover:border-blue-300 transition-all shadow-sm hover:shadow-2xl">
                    <div
                        className="mb-6 p-4 rounded-2xl bg-slate-50 w-fit group-hover:bg-blue-600 group-hover:text-white transition-colors text-slate-700">
                        {f.icon}
                    </div>
                    <h3 className="font-bold text-xl mb-3 text-slate-900">{f.title}</h3>
                    <p className="text-slate-500 text-sm leading-relaxed">{f.desc}</p>
                </div>
                ))}
            </div>
        </div>
    </section>

    {/* Panel de Control y Flujo de Usuario */}
    <section id="beneficios" className="py-24 bg-slate-900 text-white overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid lg:grid-cols-2 gap-20 items-center">
                <div>
                    <span className="text-blue-400 font-bold text-sm tracking-widest uppercase mb-4 block">Eficiencia
                        Operativa</span>
                    <h2 className="text-4xl font-bold mb-8">De la complejidad normativa a la claridad del dato</h2>

                    <div className="space-y-8">
                        <div className="flex gap-5">
                            <div className="bg-blue-600/20 p-3 rounded-xl h-fit">
                                <Briefcase className="w-6 h-6 text-blue-400" />
                            </div>
                            <div>
                                <h4 className="text-xl font-bold mb-2">Análisis de Discrepancias</h4>
                                <p className="text-slate-400 text-sm leading-relaxed">Identificación automática de
                                    brechas entre la información reportada y los requerimientos técnicos de la CSRD.</p>
                            </div>
                        </div>

                        <div className="flex gap-5">
                            <div className="bg-indigo-600/20 p-3 rounded-xl h-fit">
                                <FileCheck className="w-6 h-6 text-indigo-400" />
                            </div>
                            <div>
                                <h4 className="text-xl font-bold mb-2">Validación Humana Centralizada</h4>
                                <p className="text-slate-400 text-sm leading-relaxed">Los expertos revisan los
                                    resultados en una interfaz unificada, confirmando o ajustando las sugerencias de la
                                    IA.</p>
                            </div>
                        </div>

                        <div className="flex gap-5">
                            <div className="bg-emerald-600/20 p-3 rounded-xl h-fit">
                                <BarChart3 className="w-6 h-6 text-emerald-400" />
                            </div>
                            <div>
                                <h4 className="text-xl font-bold mb-2">Exportación de Resultados</h4>
                                <p className="text-slate-400 text-sm leading-relaxed">Descarga de informes estructurados
                                    en formato profesional listos para su integración en dictámenes de auditoría.</p>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="relative">
                    <div
                        className="bg-white/5 backdrop-blur-sm p-1 rounded-3xl border border-white/10 shadow-2xl overflow-hidden">
                        <div className="bg-slate-800 p-8 rounded-[22px]">
                            <div className="flex items-center gap-2 mb-8 border-b border-slate-700 pb-4">
                                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                                <div className="w-3 h-3 rounded-full bg-amber-500"></div>
                                <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
                                <span
                                    className="ml-4 text-xs font-mono text-slate-500 italic uppercase tracking-widest">Protocolo
                                    de Análisis V3.1</span>
                            </div>
                            <div className="space-y-6">
                                <div
                                    className="p-4 bg-slate-900 rounded-xl border border-slate-700 border-l-4 border-l-blue-500">
                                    <p className="text-xs text-blue-400 font-bold mb-1">FASE 1: PREPARACIÓN</p>
                                    <p className="text-sm text-slate-200">Carga del marco normativo vigente y
                                        calibración de indicadores.</p>
                                </div>
                                <div
                                    className="p-4 bg-slate-900 rounded-xl border border-slate-700 border-l-4 border-l-indigo-500">
                                    <p className="text-xs text-indigo-400 font-bold mb-1">FASE 2: EXTRACCIÓN</p>
                                    <p className="text-sm text-slate-200">Localización de evidencias literales y
                                        numeración de páginas reales.</p>
                                </div>
                                <div
                                    className="p-4 bg-slate-900 rounded-xl border border-slate-700 border-l-4 border-l-emerald-500">
                                    <p className="text-xs text-emerald-400 font-bold mb-1">FASE 3: EVALUACIÓN</p>
                                    <p className="text-sm text-slate-200">Razonamiento técnico sobre el cumplimiento
                                        normativo (SÍ / NO / N.A.).</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="absolute -bottom-6 -right-6 w-32 h-32 bg-blue-600/30 rounded-full blur-3xl"></div>
                </div>
            </div>
        </div>
    </section>

    {/* Call to Action Final */}
    <section className="py-24 bg-white text-center">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-4xl font-black text-slate-900 mb-6">Audite con confianza. Valide con rapidez.</h2>
            <p className="text-lg text-slate-600 mb-10 leading-relaxed">
                Únase a las firmas líderes que ya están transformando la revisión de sostenibilidad en un proceso ágil,
                riguroso y transparente.
            </p>
            <div className="flex flex-col sm:flex-row justify-center gap-4">
                <button
                    onClick={onLoginClick}
                    className="bg-blue-700 text-white px-10 py-4 rounded-xl font-bold hover:bg-blue-800 transition-all shadow-lg hover:shadow-2xl">
                    Iniciar Auditoría
                </button>
            </div>
        </div>
    </section>

    {/* Footer */}
    <footer className="bg-slate-50 border-t border-slate-200 py-12">
        <div
            className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-8 text-slate-500 text-sm">
            <div className="flex items-center gap-3">
                <ShieldCheck className="text-blue-700 w-6 h-6" />
                <span className="font-bold text-slate-900">RECAVA Auditor AI</span>
            </div>
            <p>© 2024 Observatorio de Sostenibilidad. Herramienta diseñada para el sector jurídico-financiero.</p>
        </div>
    </footer>
</div>
);
};

export default Landing;
