import re
import tabula
import pandas as pd

from Curso import Curso, Disciplina, CargaHoraria


class PDFScapper:
    @staticmethod
    def __get_course_name(tables: pd.DataFrame) -> str:
        for table in tables:
            course_name = re.findall("Curso: ([^\r]*)", table.columns[0])
            if course_name:
                return course_name[0]

    @staticmethod
    def __get_semester_tables(tables: [pd.DataFrame]) -> [pd.DataFrame]:
        semester_tables = list(
            filter(lambda df: df.columns[0][:7] == "PERÍODO", tables)
        )

        # Concatenate tables that span multiple pages
        deprecated_dfs = []
        for i, j in zip(range(len(semester_tables)), range(1, len(semester_tables))):
            if semester_tables[i].columns[0] == semester_tables[j].columns[0]:
                semester_tables[j] = pd.concat(
                    [semester_tables[i], semester_tables[j].drop(0)], ignore_index=True
                )
                deprecated_dfs.append(i)

        # Keep only the fully concatenated tables
        semester_tables = [
            df for i, df in enumerate(semester_tables) if i not in deprecated_dfs
        ]
        for df in semester_tables:
            df.columns = [
                "main",
                "tipo",
                "ch_teorica",
                "ch_pratica",
                "ch_total",
                "creditos",
            ]
            df.drop(0, inplace=True)
    
        return semester_tables

    @staticmethod
    def __get_courses(semester_tables: [pd.DataFrame]) -> [Disciplina]:
        disciplinas = []
        for i, semester in enumerate(semester_tables):
            for _, disciplina in semester.loc[semester.tipo == "OBRIG"].iterrows():
                disciplina_cod_nome = disciplina["main"].split("- ")
                disciplinas.append(
                    Disciplina(
                        disciplina_cod_nome[0],
                        disciplina_cod_nome[1],
                        i,
                        CargaHoraria(
                            disciplina["ch_teorica"], disciplina["ch_pratica"]
                        ),
                    )
                )
        return disciplinas

    @staticmethod
    def __get_course_prerequisites(
        semester_tables: [pd.DataFrame], course_code: str
    ) -> [Disciplina]:
        for semester in semester_tables:
            m = semester["tipo"].eq("OBRIG")
            cumgrp = m.cumsum()[~m]
            grps = semester[~m].groupby(cumgrp)

            for (_, disciplina), (_, group) in zip(semester[m].iterrows(), grps):
                disciplina_cod_nome = disciplina["main"].split("- ")
                if (
                    disciplina_cod_nome[0] != course_code
                ):  # There is probably a better way than this!
                    continue

                prerequisites_txt = group[
                    group["main"].str.startswith("PRÉ-REQUISITO")
                ]["main"].to_list()[0]
                prerequisites_matches = re.findall(
                    "Fórmula: \(?(.*)\)?$", prerequisites_txt
                )
                if prerequisites_matches:
                    return (
                        prerequisites_matches[0]
                        .upper()
                        .replace("(", "")
                        .replace(")", "")
                        .split(" E ")
                    )
                else:
                    return []

    @staticmethod
    def scrape(pdf_path: str) -> Curso:
        tables = tabula.read_pdf(pdf_path, pages="all", lattice="true")

        course_name = PDFScapper.__get_course_name(tables)

        semester_tables = PDFScapper.__get_semester_tables(tables)

        curso = Curso(course_name, PDFScapper.__get_courses(semester_tables))
        for disciplina in curso.disciplinas:
            disciplina.prerequisitos = [
                curso[codigo_prerequisito]
                for codigo_prerequisito in PDFScapper.__get_course_prerequisites(
                    semester_tables, disciplina.codigo
                )
            ]

        return curso

if __name__ == '__main__':
    biomed = PDFScapper.scrape('pdfs/perfil_curricular_biomed.pdf')
    biomed.perfil_curricular_dot().render('perfil_biomed')