import re
import tabula
import requests
import pandas as pd
from time import sleep
from bs4 import BeautifulSoup

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


class PDFFinder:
    url_base = "https://www.ufpe.br"
    lista_de_cursos = "/cursos/graduacao"

    def __init__(self):
        pass

    def get_courses(self):
        response = requests.get(self.url_base + self.lista_de_cursos)
        soup = BeautifulSoup(response.text, "html.parser")
        listas = soup.find_all("div", {"class": "links-column"})
        campi = {}
        for lista in listas:
            campus = lista.find_all("h4", {"class": "box-title"})[0].string
            campi[campus] = []
            for li in lista.find_all("li"):
                link_path = li.a["href"]
                curso = li.a.strong.string
                campi[campus].append((curso, link_path))
        return campi

    def get_course_profile_link(self, link_path, container_id="t-content-0"):
        response = requests.get(self.url_base + link_path)
        print(response.status_code)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.find(id=container_id).find_all("a")[0]["href"]

    def get_courses_profile_links(self):
        visited = []
        with open("course_pdflink.csv") as output_csv:
            for line in output_csv:
                if "," not in line:
                    campus = line.strip()
                else:
                    course = line.split(",")[0]
                    visited.append((campus, course))

        campi = self.get_courses()
        # with open("course_pdflink.csv", "a") as output_csv:
        #     for campus in campi:
        #         courses_pdflinks = []
        #         print(campus)
        #         output_csv.write("%s\n" % campus)
        #         for course, link_path in campi[campus]:
        #             print("\t", course)
        #             if (campus, course) in visited:
        #                 print("Already visited")
        #                 continue
        #             try:
        #                 pdf_link = self.get_course_profile_link(link_path)
        #                 courses_pdflinks.append((course, pdf_link))
        #                 output_csv.write("%s,%s\n" % (course, pdf_link))
        #             except AttributeError:
        #                 try:
        #                     pdf_link = self.get_course_profile_link(
        #                         link_path, container_id="a-content-0"
        #                     )
        #                     courses_pdflinks.append((course, pdf_link))
        #                     output_csv.write("%s,%s\n" % (course, pdf_link))
        #                 except:
        #                     print("Erro")
        #             except IndexError:
        #                 print("Erro")
        #             except ConnectionError:
        #                 print("Erro de conexão?")
        #             except Exception:
        #                 print("Erro ???")
        #             sleep(15)

        for campus in campi:
            campi[campus] = []
        with open("course_pdflink.csv") as output_csv:
            for line in output_csv:
                if "," not in line:
                    campus = line.strip()
                else:
                    line = line.split(",")
                    course, pdf_link = line[0], line[1]
                    campi[campus].append((course, pdf_link))

        return campi


if __name__ == "__main__":
    biomed = PDFScapper.scrape("pdfs/perfil_curricular_biomed.pdf")
    biomed.perfil_curricular_dot().render("perfil_biomed")
