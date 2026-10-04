# from gensim.models import Word2Vec

# # load full model (NOT KeyedVectors!)
# model = Word2Vec.load("cswiki-latest-pages-articles.word2vec")

# # extract KeyedVectors
# kv = model.wv

# # save as .kv
# kv.save("models/embeddings/wiki2vec_cz.kv")
from wikipedia2vec import Wikipedia2Vec
from gensim.models import KeyedVectors
import numpy as np

model = Wikipedia2Vec.load("dewiki_20180420_100d.pkl.bz2")

# THIS is the correct way
words = list(model.dictionary.word2index.keys())

print("Words:", len(words))

vectors = np.vstack([model.get_word_vector(w) for w in words])

kv = KeyedVectors(vector_size=vectors.shape[1])
kv.add_vectors(words, vectors)

kv.save("dewiki.kv")

print("✅ Saved dewiki.kv")