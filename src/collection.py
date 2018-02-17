import heapq
import math
import operator
from collections import defaultdict


from boolean_expression_parse import BooleanExpressionParser
from document import textpreprocess


class InvertedIndex(defaultdict):
    def __init__(self):
        super().__init__(dict)

    def add_document(self, d):
        """
        Adds a document in inverted index. It, also, calculates property L_d, which is the norm of vector of w
        as is in [chapter4-vector.pdf page 14].
        :param d: Document
        :return: L_d
        """
        l_d = 0
        for term, count in d.tokenize().items():
            # Document add
            self[term][d] = count
            # L_d calculation
            if count == 1:
                l_d += 1  # Faster for count=1, same result though
            else:
                l_d += (1 + math.log(count))**2

        return math.sqrt(l_d)


class Collection:
    def __init__(self, mongo_db=None, mongo_collections=None):
        """

        :param mongo_db: MongoClient object
        :param mongo_collections: dict with collections: 'invertedIndex' for inverted index collection (will contain
         term as key and document locations as value and 'documents' for documents collection (will contain document
         location as key and L_d as value)
        """
        self.index = InvertedIndex()  # inverted index
        self.documents = dict()  # dict with documents as keys and L_d as values
        self.mongo_db = mongo_db
        self.mongo_collections = mongo_collections

    def flush_to_mongo(self):
        # Transform index and documents in mongo format
        # mindex = [{'term': term, 'docs': [{'doc': doc.location, 'count': count} for doc, count in docs.items()]} for term, docs in self.index.items()]


        # Write the to mongo
        if self.index and self.documents:
            # self.mongo_db[self.mongo_collections['invertedIndex']].insert_many(mindex)
            for term, docs in self.index.items():
                mdocs = [{'doc': doc.location, 'count': count} for doc, count in docs.items()]
                self.mongo_db[self.mongo_collections['invertedIndex']].update({'term': term}, {"$push": {"docs": {"$each": mdocs}}}, upsert=True)
            mdocs = [{'doc': doc.location, 'L_d': L_d} for doc, L_d in self.documents.items()]
            self.mongo_db[self.mongo_collections['documents']].insert_many(mdocs)

        # Clear memory
        self.index.clear()
        self.documents.clear()

    def get_documents_count(self):
        return self.mongo_db[self.mongo_collections['invertedIndex']].count()

    def get_index_count(self):
        return self.mongo_db[self.mongo_collections['documents']].count()

    def get_documents_for_term(self, term):
        ans = self.mongo_db[self.mongo_collections['invertedIndex']].find_one({'term': term}, {'docs': 1})
        if ans:
            return ans['docs']
        else:  # Check if term is in our collection
            raise Exception("Term '" + term + "' does not exist in our inverted index.")

    def get_only_documents_for_term(self, term):
        ans = self.mongo_db[self.mongo_collections['invertedIndex']].find_one({'term': term}, {'docs': 1})
        return set([doc_entry['doc'] for doc_entry in ans['docs']]) if ans else set()

    def get_documents_not_in(self, other_doc_set):
        ans = self.mongo_db[self.mongo_collections['documents']].find({'doc': {"$nin": list(other_doc_set)}}, {'doc': 1})
        return set([doc_entry['doc'] for doc_entry in ans]) if ans else set()

    def get_document_L_d(self, doc: str):
        ans = self.mongo_db[self.mongo_collections['documents']].find_one({'doc': doc}, {'L_d': 1})
        if ans:
            return ans['L_d']
        else:  # Check if doc is in our collection
            raise Exception("Document '" + doc + "' does not exist in our collection.")

    def read_document(self, d):
        """
        Reads a document add adds its terms in inverted index. It is also adds documents' L_d in self.documents set

        :param d:
        :return:
        """
        if d not in self.documents:
            self.documents[d] = self.index.add_document(d)

    def processquery_boolean(self, q):
        """
        Processes a query with the boolean model.
        :param q: query in boolean expression format
        :return: Documents that satisfy the query
        """
        def term_documents(term):
            """ Returns documents in this index that contain term """
            return self.get_only_documents_for_term(term)

        def rest_documents(documents_set):
            """ Returns set difference between this index's documents and documents_set"""
            return self.documents.keys() - documents_set

        # get a BooleanExpressionParser, which will evaluate the query
        bparser = BooleanExpressionParser(term_documents, rest_documents)

        # process query text the same way as a document (do the same text preprocessing)
        newq = ' '.join(textpreprocess(q))

        return bparser.eval_query(newq)

    def processquery_vector(self, q, above=0.2, top=-1):
        """
        Processes a query with the vector model. Based on [chapter4-vector.pdf page 14]
        :param q: query. Any sentence
        :param above: lowest limit in similarity of documet and query. Defaults to 0.2
        :param top: Returns top x documents if is set. Defaults to unlimited (-1)
        :return: Documents that satisfy the query
        """
        q_tokens = textpreprocess(q)

        S = defaultdict(float)

        for term in q_tokens:
            idf_t = math.log(1 + self.get_documents_count() / self.get_index_count())

            for doc_entry in self.get_documents_for_term(term):
                S[doc_entry['doc']] += doc_entry['count'] * idf_t

        for d in S.keys():
            S[d] /= self.get_document_L_d(d)

        S_passed = [(k, v) for k, v in S.items() if v >= above] if above > 0 else S.items()
        return S_passed if top < 0 else heapq.nlargest(top, S_passed, key=operator.itemgetter(1))

